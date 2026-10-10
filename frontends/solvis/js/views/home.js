// Inicio: tablero con números clave, pipeline y pendientes (como el Home de Zoho).
import { api, session } from "/shared/api.js";
import { icon } from "../icons.js";
import { getMeta } from "../modules.js";
import { badge, date, emptyState, h, relDays, shortMoney } from "../ui.js";

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

export async function renderHome(page) {
  document.title = "Inicio · Solvis CRM";
  const [d, meta] = await Promise.all([api("dashboard/"), getMeta()]);
  const t = d.totals;
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Buen día" : hour < 19 ? "Buenas tardes" : "Buenas noches";
  const label = (key, v) => meta[key]?.find((c) => c.value === v)?.label || v;

  const kpi = (ic, color, lbl, value, sub, href) => h("a.card.kpi", { href, style: { color: "inherit", textDecoration: "none" } },
    h(`div.kpi-icon${color ? "." + color : ""}`, icon(ic)),
    h("div", h("div.label", lbl), h("div.value", value), sub ? h("div.sub", sub) : null));

  const maxAmount = Math.max(1, ...d.pipeline.map((s) => Number(s.amount)));
  const pipeline = d.pipeline.length
    ? h("div.bars", d.pipeline.map((s) => h("div.bar-row",
        h("a", { href: `#/deals?stage=${s.id}`, style: { color: "var(--text)", fontWeight: 500 } }, s.name),
        h("div.bar-track", h("div.bar-fill", { style: { width: `${(Number(s.amount) / maxAmount) * 100}%`, background: s.color || "var(--accent)" } })),
        h("div.bar-value", h("strong", shortMoney(s.amount)), h("span.muted.small", ` · ${s.count}`)))))
    : emptyState("Todavía no hay etapas.");

  const list = (items, render, empty) => items.length ? h("ul.mini-list", items.map(render)) : emptyState(empty);
  const totalSources = d.leads_by_source.reduce((a, s) => a + s.count, 0) || 1;

  page.append(
    h("div.welcome",
      h("div", h("h1", `${greet}, ${session.user?.first_name || session.user?.username}`),
        h("div.muted", `${session.tenant?.name || ""} · ${new Date().toLocaleDateString("es-PY", { weekday: "long", day: "numeric", month: "long" })}`))),
    h("div.kpis",
      kpi("lead", "", "Leads nuevos", t.leads_new, plural(t.leads, "lead en total", "leads en total"), "#/leads?status=NUEVO"),
      kpi("deal", "blue", "Pipeline abierto", shortMoney(t.open_amount), plural(t.open_opportunities, "oportunidad abierta", "oportunidades abiertas"), "#/deals?view=kanban"),
      kpi("trophy", "green", "Ganado este mes", shortMoney(t.won_month_amount), plural(t.won_month_count, "oportunidad", "oportunidades"), "#/deals"),
      kpi("task", "amber", "Mis tareas", t.tasks_pending, t.tasks_overdue ? plural(t.tasks_overdue, "vencida", "vencidas") : "Ninguna vencida", "#/tasks"),
    ),
    h("div.dash-grid",
      h("section.card.span-8",
        h("div.card-header", icon("chart"), h("h3", "Pipeline por etapa"), h("a.small", { href: "#/deals?view=kanban", style: { marginLeft: "auto" } }, "Ver tablero")),
        h("div.card-body", pipeline)),
      h("section.card.span-4",
        h("div.card-header", icon("filter"), h("h3", "Leads por origen")),
        h("div.card-body", d.leads_by_source.length
          ? h("div.bars", d.leads_by_source.map((s) => h("div", { style: { display: "grid", gap: "4px" } },
              h("div.row", h("span", label("lead_source", s.source)), h("span.muted", { style: { marginLeft: "auto" } }, s.count)),
              h("div.bar-track", h("div.bar-fill", { style: { width: `${(s.count / totalSources) * 100}%`, background: "var(--accent)" } })))))
          : emptyState("Sin datos de origen."))),
      h("section.card.span-4",
        h("div.card-header", icon("task"), h("h3", "Mis tareas abiertas"), h("a.small", { href: "#/tasks", style: { marginLeft: "auto" } }, "Ver todas")),
        list(d.my_tasks, (task) => h("li",
          h("div.grow", h("div.title", task.title), h("div.small", { style: { color: task.due_date && new Date(task.due_date) < new Date(new Date().toDateString()) ? "var(--danger)" : "var(--muted)" } }, task.due_date ? relDays(task.due_date) : "Sin fecha")),
          badge(task.priority, label("task_priority", task.priority))), "No tenés tareas pendientes.")),
      h("section.card.span-4",
        h("div.card-header", icon("clock"), h("h3", "Cierran este mes")),
        list(d.closing_this_month, (o) => h("li",
          h("div.grow", h("a.title", { href: `#/deals/${o.id}` }, o.name), h("div.muted.small", `${o.company__name} · ${date(o.expected_closing_date)}`)),
          h("strong.nowrap", shortMoney(o.amount))), "Nada previsto para este mes.")),
      h("section.card.span-4",
        h("div.card-header", icon("lead"), h("h3", "Leads recientes"), h("a.small", { href: "#/leads", style: { marginLeft: "auto" } }, "Ver todos")),
        list(d.recent_leads, (l) => h("li",
          h("div.grow", h("a.title", { href: `#/leads/${l.id}` }, l.name), h("div.muted.small", l.company || l.title)),
          badge(l.status, label("lead_status", l.status))), "Todavía no hay leads.")),
    ),
  );
}
