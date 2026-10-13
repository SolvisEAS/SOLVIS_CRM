"""
Lanza y ejecuta las búsquedas de la Captación.

Una búsqueda tarda varios minutos, así que corre en un proceso aparte
(`manage.py prospecting_run <id>`) y la pantalla consulta su estado.
Solo corre una a la vez por cliente, para cuidar la memoria del servidor.
"""
import os
import subprocess
import sys
from datetime import timedelta
from decimal import Decimal

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Sum
from django.utils import timezone

from core.exceptions import BusinessRuleError

from . import engine
from .models import Prospect, ProspectingSettings, SearchRun, normalize_url

MAX_RUN_TIME = timedelta(minutes=60)
START_TIMEOUT = timedelta(minutes=5)
CUT_MESSAGE = "La búsqueda se cortó antes de terminar (por ejemplo, se reinició el servidor). Probá de nuevo."


def get_settings(tenant_id):
    obj, _ = ProspectingSettings.objects.get_or_create(tenant_id=tenant_id)
    return obj


def api_key_for(cfg):
    return cfg.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")


def month_spend(tenant_id):
    start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = SearchRun.objects.filter(tenant_id=tenant_id, created_at__gte=start).aggregate(t=Sum("cost_usd"))["t"]
    return total or Decimal("0")


def process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def close_stale_runs(tenant_id):
    """Marca como cortadas las búsquedas que quedaron colgadas (ej: se reinició el servidor)."""
    now = timezone.now()
    for run in SearchRun.objects.filter(tenant_id=tenant_id, status__in=[SearchRun.Status.PENDIENTE,
                                                                        SearchRun.Status.EN_CURSO]):
        never_started = run.status == SearchRun.Status.PENDIENTE and run.created_at < now - START_TIMEOUT
        died = run.status == SearchRun.Status.EN_CURSO and run.worker_pid and not process_alive(run.worker_pid)
        if never_started or died or run.created_at < now - MAX_RUN_TIME:
            run.status = SearchRun.Status.ERROR
            run.finished_at = now
            run.error = CUT_MESSAGE
            run.save(update_fields=["status", "finished_at", "error"])


def start_run(search, user):
    cfg = get_settings(search.tenant_id)
    if not api_key_for(cfg):
        raise BusinessRuleError("Falta cargar la clave de la API de Anthropic en Captación → Configuración.",
                                "missing_api_key")
    if month_spend(search.tenant_id) >= cfg.monthly_budget_usd:
        raise BusinessRuleError(
            f"Se llegó al tope de gasto del mes (US$ {cfg.monthly_budget_usd}). Podés subirlo en Configuración.",
            "budget_reached")
    if not search.keyword_list:
        raise BusinessRuleError("La búsqueda no tiene frases para buscar.", "no_keywords")
    close_stale_runs(search.tenant_id)
    busy = [SearchRun.Status.PENDIENTE, SearchRun.Status.EN_CURSO]
    if SearchRun.objects.filter(tenant_id=search.tenant_id, status__in=busy).exists():
        raise BusinessRuleError("Ya hay una búsqueda en curso. Esperá a que termine.", "run_in_progress")
    run = SearchRun.objects.create(tenant_id=search.tenant_id, search=search, model=cfg.model, created_by=user)
    launch(run)
    return run


def launch(run):
    subprocess.Popen(
        [sys.executable, str(django_settings.BASE_DIR / "manage.py"), "prospecting_run", str(run.id)],
        cwd=django_settings.BASE_DIR, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )


def parse_date(value):
    from datetime import date

    try:
        return date.fromisoformat((value or "").strip()[:10])
    except ValueError:
        return None


def clean_email(value):
    value = (value or "").strip()
    try:
        validate_email(value)
    except ValidationError:
        return ""
    return value


def as_score(value):
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 50


def cut(name, value):
    value = str(value or "").strip()
    max_length = Prospect._meta.get_field(name).max_length
    return value[:max_length] if max_length else value


def save_prospects(run, items, date_from):
    """Guarda lo que encontró Claude, sin repetir publicaciones ya guardadas."""
    seen = set()
    for item in items:
        run.found_count += 1
        url = (item.get("source_url") or "").strip()
        url = url if url.startswith(("http://", "https://")) else ""
        key = normalize_url(url) if url else ""
        published = parse_date(item.get("published_at"))
        if published and published < date_from - timedelta(days=2):
            run.out_of_range_count += 1
            continue
        if key and (key in seen or Prospect.objects.filter(tenant_id=run.tenant_id, source_key=key).exists()):
            run.duplicate_count += 1
            continue
        if not (item.get("need") or "").strip() and not url:
            continue
        seen.add(key)
        fields = {name: cut(name, item.get(name)) for name in engine.PROSPECT_FIELDS
                  if name not in ("source_url", "published_at", "email")}
        Prospect.objects.create(
            tenant_id=run.tenant_id, search=run.search, run=run, source_url=url[:1000],
            published_at=published, email=clean_email(item.get("email")),
            score=as_score(item.get("score")),
            **{**fields, "need": fields["need"] or "Ver publicación"},
        )
        run.new_count += 1


def execute_run(run_id, client=None):
    run = SearchRun.objects.select_related("search").get(pk=run_id)
    if run.status != SearchRun.Status.PENDIENTE:
        return run
    cfg = get_settings(run.tenant_id)
    run.model = run.model or cfg.model
    run.status = SearchRun.Status.EN_CURSO
    run.worker_pid = os.getpid()
    run.started_at = timezone.now()
    run.date_to = timezone.localdate()
    run.date_from = run.date_to - timedelta(days=max(1, run.search.period_days))
    run.save()

    usage = engine.Usage(model=run.model)
    try:
        client = client or engine.make_client(api_key_for(cfg))
        known = list(Prospect.objects.filter(tenant_id=run.tenant_id).exclude(source_url="")
                     .order_by("-created_at").values_list("source_url", flat=True)[:150])
        result = engine.find_prospects(client, run.model, run.search, run.date_from, run.date_to, known, usage)
        run.summary = result.summary[:4000]
        save_prospects(run, result.prospects, run.date_from)
        run.status = SearchRun.Status.TERMINADA
    except Exception as ex:  # noqa: BLE001 - cualquier falla queda registrada en la ejecución
        run.status = SearchRun.Status.ERROR
        run.error = engine.friendly_error(ex)[:2000]
    run.finished_at = timezone.now()
    run.web_searches = usage.web_searches
    run.input_tokens = usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens
    run.output_tokens = usage.output_tokens
    run.cost_usd = usage.cost_usd.quantize(Decimal("0.0001"))
    run.save()
    return run
