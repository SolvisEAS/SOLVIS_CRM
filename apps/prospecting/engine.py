"""
Motor de la Captación: Claude (API de Anthropic) busca en internet.

Cada ejecución hace dos pedidos:
1. Investigación: Claude usa la búsqueda web y la lectura de páginas (corren en
   los servidores de Anthropic) y escribe un informe con cada posible cliente.
2. Extracción: el informe se pasa a JSON con salida estructurada para guardarlo.

La librería `anthropic` se importa recién al usarla, así el resto del CRM
funciona aunque no esté instalada.
"""
import json
from dataclasses import dataclass, field
from decimal import Decimal

# USD por millón de tokens: entrada, salida, lectura de caché, escritura de caché.
PRICES = {
    "claude-opus-5-5": (Decimal("4"), Decimal("20"), Decimal("0.20"), Decimal("5")),
    "claude-sonnet-5-5": (Decimal("2"), Decimal("10"), Decimal("0.20"), Decimal("2.5")),
}
WEB_SEARCH_USD = Decimal("0.01")  # US$ 10 cada 1.000 búsquedas

# Profundidad: búsquedas web como máximo, esfuerzo de Claude y prospectos como máximo.
DEPTH = {
    "RAPIDA": (5, "low", 8),
    "NORMAL": (10, "medium", 15),
    "PROFUNDA": (20, "high", 30),
}
COUNTRY_CODES = {
    "paraguay": "PY", "argentina": "AR", "brasil": "BR", "brazil": "BR", "uruguay": "UY", "chile": "CL",
    "bolivia": "BO", "peru": "PE", "perú": "PE", "colombia": "CO", "ecuador": "EC", "venezuela": "VE",
    "mexico": "MX", "méxico": "MX", "españa": "ES", "espana": "ES", "estados unidos": "US",
}
# Si Claude rechaza un pedido por sus filtros de seguridad, Anthropic lo reintenta con otro modelo.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_CONTINUATIONS = 6

RESEARCH_SYSTEM = """Sos el equipo de prospección comercial de Solvis, una empresa de Paraguay. Tu trabajo es encontrar en internet personas o empresas que hoy están buscando lo que Solvis vende, para que el equipo de ventas las contacte.

Qué cuenta como un buen prospecto:
- Alguien que escribió públicamente que necesita, busca, pide recomendaciones o se queja de no tener lo que Solvis vende. Por ejemplo: "¿qué CRM me recomiendan?", "busco programador para un sistema de ventas", "necesito una app para mi negocio".
- Puede estar en foros, Reddit, grupos y páginas públicas de Facebook, LinkedIn, X/Twitter, Instagram, sitios de preguntas y respuestas, comentarios en blogs o YouTube, clasificados o portales de proyectos freelance (Workana, Freelancer y similares).

Qué NO cuenta:
- Empresas que venden su propio CRM o software (competencia), agencias que ofrecen servicios, avisos de empleo para programadores, notas de prensa, artículos generales y spam.
- Publicaciones fuera del período pedido.

Privacidad (obligatorio):
- Usá solo información pública, visible sin iniciar sesión.
- Nunca inventes ni deduzcas datos de contacto. Anotá solo los correos, teléfonos, WhatsApp, usuarios de redes o webs que la persona o su empresa publicaron. Si no dejó ninguno, el contacto es el link de la publicación, para responderle ahí.
- No anotes datos sensibles: salud, religión, política, documentos de identidad ni datos de menores.

Cómo trabajar:
- Probá varias formas de decir lo mismo, en el idioma de cada país, con comillas y operadores como site:reddit.com o site:facebook.com, y frases como "recomienden", "alguien conoce", "busco", "necesito".
- Abrí con web_fetch las publicaciones prometedoras para confirmar la fecha, qué pide y si dejó algún contacto.
- Preferí calidad a cantidad: 5 prospectos reales valen más que 20 dudosos.

Al terminar, escribí un informe con:
1. Un resumen de 2 o 3 frases: dónde encontraste demanda y qué tipo de gente la pide.
2. La lista de prospectos. Para cada uno: nombre o usuario; empresa si se sabe; qué necesita, en una frase; una cita textual corta de lo que escribió; el link exacto de la publicación; el nombre del sitio; la fecha de publicación (AAAA-MM-DD, o "desconocida"); ciudad o país; todos los contactos públicos que encontraste; y un puntaje de interés de 0 a 100 con su motivo (100 = pide exactamente lo que Solvis vende y lo necesita ya)."""

EXTRACT_SYSTEM = """Convertí un informe de prospección en datos estructurados.
- Copiá solo lo que dice el informe. No inventes nada.
- Un elemento por prospecto. Los campos sin dato van como cadena vacía.
- published_at en formato AAAA-MM-DD, o vacío si la fecha es desconocida.
- score es un entero de 0 a 100.
- source_url es el link exacto de la publicación tal como figura en el informe.
- summary es el resumen del informe, en 2 o 3 frases."""

PROSPECT_FIELDS = (
    "name", "company", "need", "quote", "source_url", "source_name", "published_at", "location",
    "email", "phone", "whatsapp", "instagram", "facebook", "linkedin", "twitter", "website",
    "other_contact", "score_reason",
)
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "prospects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {**{f: {"type": "string"} for f in PROSPECT_FIELDS}, "score": {"type": "integer"}},
                "required": [*PROSPECT_FIELDS, "score"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "prospects"],
    "additionalProperties": False,
}


class EngineError(Exception):
    """Error con un mensaje para mostrarle al usuario tal cual."""


@dataclass
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    web_searches: int = 0

    def add(self, usage):
        if usage is None:
            return
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_write_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        server = getattr(usage, "server_tool_use", None)
        self.web_searches += getattr(server, "web_search_requests", 0) or 0

    @property
    def cost_usd(self):
        """Costo estimado según la lista de precios (la factura real la da Anthropic)."""
        p_in, p_out, p_read, p_write = PRICES.get(self.model, PRICES["claude-opus-5-5"])
        million = Decimal(1_000_000)
        return (
            self.input_tokens * p_in + self.output_tokens * p_out
            + self.cache_read_tokens * p_read + self.cache_write_tokens * p_write
        ) / million + self.web_searches * WEB_SEARCH_USD


@dataclass
class Result:
    summary: str
    prospects: list = field(default_factory=list)


def make_client(api_key):
    try:
        import anthropic
    except ImportError as ex:
        raise EngineError("Falta instalar la librería de Anthropic en el servidor.") from ex
    return anthropic.Anthropic(api_key=api_key)


def user_location(countries):
    """Localiza la búsqueda web cuando se pide un solo país conocido."""
    names = [c.strip().lower() for c in countries.split(",") if c.strip()]
    if len(names) != 1 or names[0] not in COUNTRY_CODES:
        return None
    code = COUNTRY_CODES[names[0]]
    location = {"type": "approximate", "country": code}
    if code == "PY":
        location["timezone"] = "America/Asuncion"
    return location


def research_prompt(search, date_from, date_to, known_urls, max_prospects):
    keywords = "\n".join(f"- {k}" for k in search.keyword_list)
    known = "\n".join(f"- {u}" for u in known_urls) or "(ninguna todavía)"
    return (
        f"Buscá prospectos para esta búsqueda.\n\n"
        f"Qué ofrece Solvis: {search.offering or 'CRM y desarrollo de software a medida'}\n"
        f"Frases o temas a buscar:\n{keywords}\n"
        f"Países: {search.countries or 'cualquiera de habla hispana'}\n"
        f"Período: solo publicaciones entre el {date_from:%Y-%m-%d} y el {date_to:%Y-%m-%d} (hoy es {date_to:%Y-%m-%d}).\n"
        f"Cantidad máxima de prospectos: {max_prospects}\n\n"
        f"Estas publicaciones ya están guardadas, no las repitas:\n{known}"
    )


def check_refusal(response):
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None) if details else None
        raise EngineError(f"Claude no quiso hacer esta búsqueda{f' (motivo: {category})' if category else ''}. "
                          "Probá con otras palabras.")


def research(client, model, search, date_from, date_to, known_urls, usage):
    max_searches, effort, max_prospects = DEPTH.get(search.depth, DEPTH["NORMAL"])
    web_search = {"type": "web_search_20260318", "name": "web_search", "max_uses": max_searches,
                  "response_inclusion": "excluded"}
    location = user_location(search.countries)
    if location:
        web_search["user_location"] = location
    tools = [web_search, {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": max_searches,
                          "max_content_tokens": 8000}]
    messages = [{"role": "user", "content": research_prompt(search, date_from, date_to, known_urls, max_prospects)}]
    texts = []
    for _ in range(MAX_CONTINUATIONS):
        with client.beta.messages.stream(
            model=model, max_tokens=32000, system=RESEARCH_SYSTEM, messages=messages, tools=tools,
            output_config={"effort": effort}, betas=[FALLBACK_BETA], fallbacks="default",
        ) as stream:
            response = stream.get_final_message()
        usage.add(response.usage)
        check_refusal(response)
        texts += [b.text for b in response.content if b.type == "text" and b.text.strip()]
        if response.stop_reason != "pause_turn":
            break
        # La búsqueda web hizo una pausa larga: se reenvía lo hecho y Anthropic continúa.
        messages.append({"role": "assistant", "content": response.content})
    report = "\n\n".join(texts).strip()
    if not report:
        raise EngineError("Claude terminó sin escribir resultados. Probá de nuevo o con otras palabras.")
    return report


def extract(client, model, report, usage):
    response = client.beta.messages.create(
        model=model, max_tokens=16000, system=EXTRACT_SYSTEM,
        messages=[{"role": "user", "content": f"<informe>\n{report}\n</informe>"}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": EXTRACT_SCHEMA}},
        betas=[FALLBACK_BETA], fallbacks="default",
    )
    usage.add(response.usage)
    check_refusal(response)
    if response.stop_reason == "max_tokens":
        raise EngineError("La lista de resultados salió demasiado larga. Probá con una búsqueda más acotada.")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except ValueError as ex:
        raise EngineError("No se pudo leer la respuesta de Claude. Probá de nuevo.") from ex
    return Result(summary=data.get("summary", ""), prospects=data.get("prospects", []))


def find_prospects(client, model, search, date_from, date_to, known_urls, usage):
    report = research(client, model, search, date_from, date_to, known_urls, usage)
    return extract(client, model, report, usage)


def friendly_error(ex):
    """Mensaje claro para los errores de la API de Anthropic."""
    if isinstance(ex, EngineError):
        return str(ex)
    try:
        import anthropic
    except ImportError:
        return f"Error inesperado: {ex}"
    if isinstance(ex, anthropic.AuthenticationError):
        return "La clave de la API de Anthropic no es válida. Revisala en Captación → Configuración."
    if isinstance(ex, anthropic.PermissionDeniedError):
        return "La clave de Anthropic no tiene permiso para esto (o la búsqueda web está desactivada en la cuenta)."
    if isinstance(ex, anthropic.NotFoundError):
        return "Anthropic no reconoce el modelo elegido. Elegí otro en Captación → Configuración."
    if isinstance(ex, anthropic.RateLimitError):
        return "Anthropic está recibiendo demasiados pedidos de esta cuenta. Probá de nuevo en unos minutos."
    if isinstance(ex, anthropic.BadRequestError):
        message = str(getattr(ex, "message", ex))
        if "credit" in message.lower() or "billing" in message.lower():
            return "La cuenta de Anthropic no tiene saldo. Cargá crédito en console.anthropic.com (Billing)."
        return f"Anthropic rechazó el pedido: {message}"
    if isinstance(ex, anthropic.APIStatusError):
        return "Anthropic tuvo un problema de su lado. Probá de nuevo más tarde."
    if isinstance(ex, anthropic.APIConnectionError):
        return "No se pudo conectar con Anthropic. Revisá la conexión del servidor."
    return f"Error inesperado: {ex}"


def check_key(api_key, model):
    """Prueba la clave sin gastar: consulta el modelo elegido."""
    client = make_client(api_key)
    try:
        info = client.models.retrieve(model)
    except Exception as ex:  # noqa: BLE001 - se traduce a un mensaje para el usuario
        raise EngineError(friendly_error(ex)) from ex
    return getattr(info, "display_name", model)
