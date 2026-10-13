// Captación (solo personal de Solvis): gente que pide en internet lo que vende Solvis.
// Claude busca publicaciones públicas; acá se revisan, se contactan y se convierten en venta.
import { api, session } from "/shared/api.js";
import { icon } from "../icons.js";
import { getStages } from "../modules.js";
import { badge, confirmDialog, date, datetime, debounce, emptyState, h, modal, spinner, toast } from "../ui.js";

const STATUS = [["NUEVO", "Nuevo"], ["CONTACTADO", "Contactado"], ["RESPONDIO", "Respondió"], ["DESCARTADO", "Descartado"], ["CONVERTIDO", "Convertido"]];
const statusLabel = (s) => STATUS.find(([v]) => v === s)?.[1] || s;
const PERIODS = [[1, "Último día"], [7, "Última semana"], [14, "Últimas 2 semanas"], [30, "Último mes"], [90, "Últimos 3 meses"]];
const periodLabel = (d) => PERIODS.find(([v]) => v === d)?.[1] || `Últimos ${d} días`;
const DEPTHS = [["RAPIDA", "Rápida", "hasta 5 búsquedas en internet"], ["NORMAL", "Normal", "hasta 10 búsquedas en internet"], ["PROFUNDA", "Profunda", "hasta 20 búsquedas en internet"]];
const OFFERING = "CRM y desarrollo de software a medida (sistemas, páginas web, apps)";
const SUGGESTED = [
  { name: "Buscan un CRM", keywords: "recomienden un CRM\nqué CRM usan\nbusco sistema para gestionar clientes\nnecesito un CRM para mi empresa" },
  { name: "Buscan un desarrollador", keywords: "busco programador para un sistema\nnecesito desarrollar un sistema a medida\nbusco quién me haga una app\npresupuesto para desarrollo de software" },
  { name: "Buscan sistema de ventas", keywords: "sistema de ventas para mi negocio\nsoftware de facturación y stock\nrecomienden un sistema para pymes" },
];
const CHANNELS = {
  email: ["Correo", "mail"], phone: ["Teléfono", "phone"], whatsapp: ["WhatsApp", "whatsapp"], instagram: ["Instagram", "instagram"],
  facebook: ["Facebook", "globe"], linkedin: ["LinkedIn", "globe"], twitter: ["X / Twitter", "globe"], website: ["Web", "globe"], other_contact: ["Otro", "note"],
};
const TABS = [["", "Prospectos", "users"], ["searches", "Búsquedas", "search"], ["settings", "Configuración", "settings"]];
const usd = (v) => `US$ ${Number(v || 0).toFixed(2).replace(".", ",")}`;
const ACTIVE = ["PENDIENTE", "EN_CURSO"];

// Los datos vienen de internet: solo se aceptan links http(s).
function safeUrl(v) {
  try { const u = new URL(v); return ["http:", "https:"].includes(u.protocol) ? u.href : null; } catch { return null; }
}
function channelHref(field, value) {
  const v = String(value || "").trim();
  if (!v) return null;
  const digits = v.replace(/[^\d]/g, "");
  const handle = v.replace(/^@/, "");
  if (field === "email") return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? `mailto:${v}` : null;
  if (field === "phone") return digits.length >= 6 ? `tel:+${digits}` : null;
  if (field === "whatsapp") return digits.length >= 8 ? `https://wa.me/${digits}` : null;
  if (/^https?:\/\//i.test(v)) return safeUrl(v);
  if (field === "instagram" && /^[\w.]+$/.test(handle)) return `https://instagram.com/${handle}`;
  if (field === "twitter" && /^\w+$/.test(handle)) return `https://x.com/${handle}`;
  if (field === "website" && /^[\w.-]+\.[a-z]{2,}(\/.*)?$/i.test(v)) return safeUrl(`https://${v}`);
  return null;
}
const ext = (href, ...children) => h("a", { href, target: "_blank", rel: "noopener noreferrer" }, ...children);
function ago(v) {
  if (!v) return "";
  const s = Math.max(0, (Date.now() - new Date(v)) / 1000);
  if (s < 60) return "recién";
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  if (s < 86400) return `hace ${Math.round(s / 3600)} h`;
  return `hace ${Math.round(s / 86400)} días`;
}
function scorePill(score) {
  const cls = score >= 75 ? "high" : score >= 50 ? "mid" : "low";
  return h(`span.score.${cls}`, { title: "Interés estimado (0 a 100)" }, String(score));
}
function kpi(ic, color, label, value, sub) {
  return h("div.card.kpi", h(`div.kpi-icon${color ? "." + color : ""}`, icon(ic)), h("div", h("div.label", label), h("div.value", value), h("div.sub", sub)));
}

export async function renderProspecting(page, tab = "", query = new URLSearchParams()) {
  if (!session.user?.is_staff) {
    page.append(h("div.card", emptyState("Esta sección es solo para el personal de Solvis.", "close")));
    return;
  }
  tab = TABS.some(([t]) => t === tab) ? tab : "";
  document.title = "Captación · Solvis CRM";
  const [stats, runs] = await Promise.all([api("prospecting/stats/"), api("prospecting/runs/", { params: { page_size: 1 } })]);
  const rerender = () => { page.replaceChildren(); return renderProspecting(page, tab, query); };

  const lastRun = runs.results[0];
  const running = lastRun && ACTIVE.includes(lastRun.status) ? lastRun : null;
  const runBox = h("div");
  if (running) watchRun(running, runBox, rerender);

  page.append(
    h("div.page-header",
      h("div", h("h1", "Captación"), h("div.muted", "Gente que pide en internet lo que vende Solvis. Solo lo ve el equipo Solvis.")),
      h("div.grow"),
      h("button.btn", { onclick: () => prospectModal(null, rerender) }, icon("plus"), "Agregar a mano"),
      h("button.btn.btn-primary", { onclick: () => searchModal(null, () => { location.hash = "#/prospecting/searches"; rerender(); }) }, icon("search"), "Nueva búsqueda")),
    h("div.btn-group.tabs", TABS.map(([t, label, ic]) => h(`a.btn${t === tab ? ".active" : ""}`, { href: `#/prospecting${t ? "/" + t : ""}` }, icon(ic), label))),
    stats.has_api_key || tab === "settings" ? null : h("div.card.notice",
      icon("key"), h("div", h("strong", "Falta un paso para que Claude pueda buscar"), h("div.muted", "Cargá la clave de la API de Anthropic en Configuración. Te explico ahí cómo sacarla.")),
      h("a.btn.btn-primary", { href: "#/prospecting/settings" }, "Ir a Configuración")),
    runBox,
    h("div.kpis",
      kpi("lead", "blue", "Nuevos", stats.by_status.NUEVO, `${stats.new_this_week} encontrados esta semana`),
      kpi("phone", "amber", "Contactados", stats.by_status.CONTACTADO + stats.by_status.RESPONDIO, `${stats.by_status.RESPONDIO} respondieron`),
      kpi("deal", "green", "Convertidos", stats.by_status.CONVERTIDO, "pasaron a oportunidad de venta"),
      kpi("chart", "", "Gasto del mes", usd(stats.month_spend_usd), `de un tope de ${usd(stats.monthly_budget_usd)}`)),
  );
  const body = h("div");
  page.append(body);
  if (tab === "searches") return renderSearches(body, rerender, !!running);
  if (tab === "settings") return renderSettingsTab(body, rerender);
  return renderProspects(body, stats, query, rerender);
}

// ---------- Búsqueda en curso ----------
function watchRun(run, box, onDone) {
  const draw = (r) => box.replaceChildren(h("div.card.notice.running",
    h("div.spinner.inline"),
    h("div", h("strong", `Claude está buscando: ${r.search_name}`),
      h("div.muted", `${r.status === "PENDIENTE" ? "Arrancando" : "Empezó " + ago(r.started_at)}. Suele tardar entre 2 y 8 minutos; podés seguir usando el CRM.`))));
  draw(run);
  const timer = setInterval(async () => {
    if (!box.isConnected) return clearInterval(timer);
    let r;
    try { r = await api(`prospecting/runs/${run.id}/`); } catch { return; }
    if (ACTIVE.includes(r.status)) return draw(r);
    clearInterval(timer);
    if (r.status === "TERMINADA") toast(`Terminó la búsqueda: ${r.new_count} prospectos nuevos (${usd(r.cost_usd)})`, "success");
    else toast(r.error || "La búsqueda terminó con un error.", "error");
    onDone();
  }, 5000);
}

// ---------- Prospectos ----------
async function renderProspects(box, stats, query, rerender) {
  const searches = await api("prospecting/searches/");
  const state = { page: 1, status: query.get("status") ?? "NUEVO", search_id: query.get("search_id") || "", has_contact: false, text: "", ordering: "-created_at" };
  const statusSel = h("select.select", { onchange: () => { state.status = statusSel.value; state.page = 1; load(); } },
    h("option", { value: "" }, "Todos los estados"), STATUS.map(([v, l]) => h("option", { value: v, selected: v === state.status }, `${l} (${stats.by_status[v]})`)));
  const searchSel = h("select.select", { onchange: () => { state.search_id = searchSel.value; state.page = 1; load(); } },
    h("option", { value: "" }, "Todas las búsquedas"), searches.map((s) => h("option", { value: s.id, selected: String(s.id) === state.search_id }, s.name)));
  const orderSel = h("select.select", { onchange: () => { state.ordering = orderSel.value; state.page = 1; load(); } },
    [["-created_at", "Más recientes"], ["-score", "Más interesados"], ["-published_at", "Publicados hace menos"]].map(([v, l]) => h("option", { value: v }, l)));
  const contactChk = h("input.checkbox", { type: "checkbox", onchange: () => { state.has_contact = contactChk.checked; state.page = 1; load(); } });
  const text = h("input.input", { type: "search", placeholder: "Buscar por nombre, necesidad o sitio…",
    oninput: debounce(() => { state.text = text.value.trim(); state.page = 1; load(); }, 300) });
  const tableWrap = h("div.table-wrap");
  const pager = h("div.pager");
  box.append(h("section.card",
    h("div.toolbar.wrap", h("div", { style: { flex: "1 1 220px" } }, text), statusSel, searchSel, orderSel, h("label.row.small", contactChk, "Solo con contacto")),
    tableWrap, pager));

  async function load() {
    tableWrap.replaceChildren(spinner());
    const data = await api("prospecting/prospects/", { params: {
      page: state.page, page_size: 25, status: state.status, search_id: state.search_id, ordering: state.ordering,
      search: state.text, has_contact: state.has_contact ? 1 : "",
    } });
    if (!data.results.length) {
      tableWrap.replaceChildren(stats.total ? emptyState("No hay prospectos con estos filtros.")
        : emptyState("Todavía no hay prospectos. Creá una búsqueda y tocá «Buscar ahora», o agregá uno a mano.", "search"));
      pager.replaceChildren();
      return;
    }
    tableWrap.replaceChildren(h("table.grid",
      h("thead", h("tr", ["Interés", "Quién y qué necesita", "De dónde viene", "Contacto", "Estado", ""].map((x) => h("th.no-sort", x)))),
      h("tbody", data.results.map((p) => h("tr.clickable", { onclick: (e) => { if (!e.target.closest("a, button")) openProspect(p, load); } },
        h("td", scorePill(p.score)),
        h("td", { style: { maxWidth: "420px" } },
          h("div.cell-name", p.name || p.company || "Sin nombre", p.name && p.company ? h("span.muted", ` · ${p.company}`) : ""),
          h("div", p.need), p.quote ? h("div.muted.small.clamp", `“${p.quote}”`) : null),
        h("td", h("div", safeUrl(p.source_url) ? ext(p.source_url, p.source_name || "Ver publicación", " ", icon("external", "inline")) : (p.source_name || "—")),
          h("div.muted.small", [p.published_at ? `Publicado ${date(p.published_at)}` : "Fecha desconocida", p.location].filter(Boolean).join(" · "))),
        h("td", contactIcons(p)),
        h("td", badge(p.status, p.status_label)),
        h("td", h("button.btn.btn-sm", { onclick: () => openProspect(p, load) }, "Ver")))))));
    const pages = Math.max(1, Math.ceil(data.count / 25));
    pager.replaceChildren(h("span", `${data.count} prospectos`), h("span.grow"),
      h("button.btn.btn-sm", { disabled: state.page <= 1, onclick: () => { state.page--; load(); } }, "Anterior"),
      h("span", `Página ${state.page} de ${pages}`),
      h("button.btn.btn-sm", { disabled: state.page >= pages, onclick: () => { state.page++; load(); } }, "Siguiente"));
  }
  load();
}

function contactIcons(p) {
  const links = Object.entries(CHANNELS).filter(([f]) => p[f]).map(([f, [label, ic]]) => {
    const href = channelHref(f, p[f]);
    const el = href ? ext(href, icon(ic)) : h("span", icon(ic));
    el.className = `contact-icon${f === "whatsapp" ? " wa" : ""}`;
    el.title = `${label}: ${p[f]}`;
    return el;
  });
  return links.length ? h("div.row", { style: { gap: "4px" } }, links) : h("span.muted.small", "Responder en la publicación");
}

async function setStatus(p, status, done) {
  try {
    await api(`prospecting/prospects/${p.id}/`, { method: "PATCH", body: { status } });
    toast(`Marcado como ${statusLabel(status).toLowerCase()}`, "success");
    done();
  } catch (ex) { toast(ex.message, "error"); }
}

function openProspect(p, onChange) {
  const item = (k, v) => (v ? h("div.detail-item.full", h("div.k", k), h("div.v", v)) : null);
  const contacts = Object.entries(CHANNELS).filter(([f]) => p[f]).map(([f, [label, ic]]) => {
    const href = channelHref(f, p[f]);
    return h("div.row", icon(ic), h("span.muted", `${label}:`), href ? ext(href, p[f]) : h("span", p[f]));
  });
  const notes = h("textarea.textarea", { placeholder: "Qué le escribiste, qué respondió, próximos pasos…" }, p.notes || "");
  const done = () => { m.close(); onChange(); };
  const converted = p.status === "CONVERTIDO";
  const m = modal({
    title: p.name || p.company || "Prospecto",
    width: "760px",
    body: [
      h("div.row", { style: { flexWrap: "wrap" } }, scorePill(p.score), badge(p.status, p.status_label),
        p.search_name ? h("span.muted.small", `Búsqueda: ${p.search_name}`) : null, h("span.muted.small", `Encontrado ${datetime(p.created_at)}`)),
      h("div.details.one",
        item("Qué necesita", p.need),
        item("Lo que dijo", p.quote ? h("blockquote.quote", p.quote) : null),
        item("De dónde viene", h("div", safeUrl(p.source_url) ? ext(p.source_url, `${p.source_name || "Abrir publicación"} `, icon("external", "inline")) : (p.source_name || "—"),
          h("div.muted.small", [p.published_at ? `Publicado el ${date(p.published_at)}` : "Fecha de publicación desconocida", p.location].filter(Boolean).join(" · ")))),
        item("Cómo contactarlo", contacts.length ? h("div.stack", { style: { gap: "6px" } }, contacts)
          : h("span.muted", "No dejó datos públicos. Respondele en la publicación.")),
        item("Por qué es buen prospecto", p.score_reason),
        item("Contactado", p.contacted_at ? datetime(p.contacted_at) : null),
        converted && p.converted_opportunity ? item("Convertido en", h("div.row",
          h("a", { href: `#/deals/${p.converted_opportunity}`, onclick: () => m.close() }, "Ver oportunidad"),
          p.converted_contact ? h("a", { href: `#/contacts/${p.converted_contact}`, onclick: () => m.close() }, "Ver contacto") : null)) : null),
      h("div.field", h("label", "Notas"), notes),
    ],
    footer: [
      h("button.btn.btn-ghost", { style: { marginRight: "auto" }, onclick: () => { m.close(); prospectModal(p, onChange); } }, icon("edit"), "Editar"),
      h("button.btn", { onclick: async () => {
        try { await api(`prospecting/prospects/${p.id}/`, { method: "PATCH", body: { notes: notes.value } }); toast("Notas guardadas", "success"); done(); }
        catch (ex) { toast(ex.message, "error"); }
      } }, "Guardar notas"),
      converted ? null : [
        p.status === "DESCARTADO" ? h("button.btn", { onclick: () => setStatus(p, "NUEVO", done) }, "Recuperar")
          : h("button.btn", { onclick: () => setStatus(p, "DESCARTADO", done) }, "Descartar"),
        p.status === "NUEVO" ? h("button.btn", { onclick: () => setStatus(p, "CONTACTADO", done) }, icon("check"), "Ya lo contacté") : null,
        p.status === "CONTACTADO" ? h("button.btn", { onclick: () => setStatus(p, "RESPONDIO", done) }, icon("check"), "Respondió") : null,
        h("button.btn.btn-primary", { onclick: () => { m.close(); convertModal(p, onChange); } }, icon("convert"), "Convertir en venta"),
      ],
    ],
  });
}

async function convertModal(p, onChange) {
  const stages = (await getStages()).filter((s) => s.is_active !== false && !s.is_won && !s.is_lost);
  const createOpp = h("input.checkbox", { type: "checkbox", checked: true });
  const name = h("input.input", { value: (p.need || "").slice(0, 120) });
  const amount = h("input.input", { type: "number", min: 0, step: "any", placeholder: "0" });
  const stage = h("select.select", stages.map((s) => h("option", { value: s.id }, s.name)));
  const oppFields = h("div.stack", h("div.field", h("label", "Nombre de la oportunidad"), name),
    h("div.field", h("label", "Monto estimado"), amount), h("div.field", h("label", "Etapa"), stage));
  createOpp.addEventListener("change", () => oppFields.classList.toggle("hidden", !createOpp.checked));
  const m = modal({
    title: `Convertir a ${p.name || p.company || "este prospecto"}`,
    body: [
      h("p", { style: { margin: 0 } }, "Se crean la empresa y el contacto en el CRM, con el origen y los datos de contacto en la descripción. El lead queda en Leads con origen «Captación web»."),
      h("label.row", createOpp, "Crear también una oportunidad de venta"),
      oppFields,
    ],
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async (e) => {
      e.target.disabled = true;
      try {
        const r = await api(`prospecting/prospects/${p.id}/convert/`, { method: "POST", body: {
          create_opportunity: createOpp.checked, opportunity_name: name.value.trim(), amount: amount.value || 0, stage: Number(stage.value) || null,
        } });
        m.close();
        onChange();
        const done = modal({
          title: "¡Listo, convertido!",
          body: h("p", { style: { margin: 0 } }, r.opportunity ? "Se crearon el contacto y la oportunidad de venta." : "Se creó el contacto."),
          footer: [h("button.btn", { onclick: () => done.close() }, "Seguir en Captación"),
            h("a.btn", { href: `#/contacts/${r.contact}`, onclick: () => done.close() }, "Ver contacto"),
            r.opportunity ? h("a.btn.btn-primary", { href: `#/deals/${r.opportunity}`, onclick: () => done.close() }, "Ver oportunidad") : null],
        });
      } catch (ex) { e.target.disabled = false; toast(ex.message, "error"); }
    } }, "Convertir")],
  });
}

function prospectModal(p, done) {
  const fields = [
    ["name", "Nombre o usuario"], ["company", "Empresa"], ["need", "Qué necesita", true], ["quote", "Lo que dijo", false, "textarea"],
    ["source_url", "Link de la publicación"], ["source_name", "Sitio (ej: Facebook)"], ["published_at", "Fecha de publicación", false, "date"],
    ["location", "Ciudad o país"], ...Object.entries(CHANNELS).map(([f, [label]]) => [f, label]), ["score", "Interés (0 a 100)", false, "number"],
  ];
  const inputs = Object.fromEntries(fields.map(([k, , , type]) => [k, type === "textarea"
    ? h("textarea.textarea", p?.[k] || "")
    : h("input.input", { type: type || "text", value: p?.[k] ?? (k === "score" ? 50 : ""), min: type === "number" ? 0 : undefined, max: type === "number" ? 100 : undefined })]));
  const m = modal({
    title: p ? "Editar prospecto" : "Agregar prospecto a mano",
    width: "640px",
    body: fields.map(([k, label, required]) => h(`div.field${required ? ".required" : ""}`, h("label", label), inputs[k])),
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async () => {
      const body = Object.fromEntries(Object.entries(inputs).map(([k, el]) => [k, el.value.trim()]));
      body.published_at ||= null;
      body.score = Math.max(0, Math.min(100, Number(body.score) || 0));
      if (!body.need) return toast("Escribí qué necesita.", "error");
      try {
        await api(p ? `prospecting/prospects/${p.id}/` : "prospecting/prospects/", { method: p ? "PATCH" : "POST", body });
        m.close(); toast(p ? "Prospecto actualizado" : "Prospecto agregado", "success"); done();
      } catch (ex) { toast(ex.message, "error"); }
    } }, p ? "Guardar" : "Agregar")],
  });
}

// ---------- Búsquedas ----------
async function renderSearches(box, rerender, busy) {
  const searches = await api("prospecting/searches/");
  if (!searches.length) {
    box.append(h("section.card", h("div.empty",
      icon("search"), h("h3", { style: { margin: "6px 0" } }, "Todavía no hay búsquedas"),
      h("p.muted", "Una búsqueda le dice a Claude qué frases buscar en internet, en qué países y en qué período."),
      h("div.row", { style: { justifyContent: "center", flexWrap: "wrap" } },
        h("button.btn.btn-primary", { onclick: async (e) => {
          e.target.disabled = true;
          try {
            for (const s of SUGGESTED) await api("prospecting/searches/", { method: "POST", body: { ...s, offering: OFFERING, countries: "Paraguay", period_days: 30, depth: "NORMAL" } });
            toast("Se crearon 3 búsquedas sugeridas", "success"); rerender();
          } catch (ex) { e.target.disabled = false; toast(ex.message, "error"); }
        } }, "Crear 3 búsquedas sugeridas"),
        h("button.btn", { onclick: () => searchModal(null, rerender) }, "Crear la mía")))));
    return;
  }
  const runNow = async (s, btn) => {
    btn.disabled = true;
    try {
      await api(`prospecting/searches/${s.id}/run/`, { method: "POST" });
      toast("Claude empezó a buscar. Te aviso cuando termine.", "success");
      rerender();
    } catch (ex) { btn.disabled = false; toast(ex.message, "error"); }
  };
  box.append(h("div.search-cards", searches.map((s) => {
    const r = s.last_run;
    const runBtn = h("button.btn.btn-primary", { disabled: busy || !s.is_active, onclick: () => runNow(s, runBtn) }, icon("search"), "Buscar ahora");
    return h("section.card.search-card",
      h("div.card-header", h("h3", s.name), s.is_active ? null : badge("DESCARTADO", "Pausada"), h("span.grow"),
        h("a.small", { href: `#/prospecting?search_id=${s.id}&status=`, title: "Ver sus prospectos" }, `${s.prospects_count} prospectos`)),
      h("div.card-body.stack", { style: { gap: "10px" } },
        h("div.chips", s.keywords.split("\n").map((k) => h("span.chip", k))),
        h("div.muted.small", `${s.countries || "Cualquier país"} · ${periodLabel(s.period_days)} · ${DEPTHS.find(([v]) => v === s.depth)?.[1] || s.depth}`),
        h("div.small", r ? [badge(r.status, r.status_label), " ",
          r.status === "TERMINADA" ? `${r.new_count} nuevos de ${r.found_count} encontrados · ${usd(r.cost_usd)} · ${ago(r.finished_at)}`
            : r.status === "ERROR" ? h("span", { style: { color: "var(--danger)" } }, r.error) : ago(r.created_at)]
          : h("span.muted", "Nunca se ejecutó")),
        h("div.row", { style: { flexWrap: "wrap" } }, runBtn,
          h("button.btn", { onclick: () => searchModal(s, rerender) }, icon("edit"), "Editar"),
          h("button.btn", { onclick: () => runsModal(s) }, icon("history"), "Historial"),
          h("button.btn.btn-ghost.btn-icon", { title: "Eliminar", onclick: async () => {
            if (!(await confirmDialog(`Eliminar «${s.name}»`, "Se borra la búsqueda y su historial. Los prospectos que encontró se quedan."))) return;
            await api(`prospecting/searches/${s.id}/`, { method: "DELETE" }); toast("Búsqueda eliminada", "success"); rerender();
          } }, icon("trash")))));
  })));
}

function searchModal(s, done) {
  const name = h("input.input", { value: s?.name || "", placeholder: "Ej: Buscan un CRM en Paraguay" });
  const keywords = h("textarea.textarea", { placeholder: "Una frase por línea, como la escribiría el cliente:\nrecomienden un CRM\nbusco programador para un sistema" }, s?.keywords || "");
  const offering = h("textarea.textarea", { style: { minHeight: "60px" } }, s?.offering ?? OFFERING);
  const countries = h("input.input", { value: s?.countries ?? "Paraguay", placeholder: "Paraguay, Argentina" });
  const period = h("select.select", PERIODS.map(([v, l]) => h("option", { value: v, selected: v === (s?.period_days || 30) }, l)));
  const depth = h("select.select", DEPTHS.map(([v, l, d]) => h("option", { value: v, selected: v === (s?.depth || "NORMAL") }, `${l} (${d})`)));
  const active = h("input.checkbox", { type: "checkbox", checked: s ? s.is_active : true });
  const m = modal({
    title: s ? `Editar «${s.name}»` : "Nueva búsqueda",
    width: "640px",
    body: [
      h("div.field.required", h("label", "Nombre"), name),
      h("div.field.required", h("label", "Frases a buscar"), keywords),
      h("div.field", h("label", "Qué vendemos"), offering),
      h("div.field", h("label", "Países"), countries),
      h("div.field", h("label", "Período"), period),
      h("div.field", h("label", "Profundidad"), h("div.stack", { style: { gap: "4px" } }, depth,
        h("span.muted.small", "Más profunda encuentra más, pero cuesta más. Normal suele andar bien."))),
      h("label.row", active, "Búsqueda activa"),
    ],
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async () => {
      const body = { name: name.value.trim(), keywords: keywords.value, offering: offering.value.trim(), countries: countries.value.trim(),
        period_days: Number(period.value), depth: depth.value, is_active: active.checked };
      if (!body.name) return toast("Ponele un nombre.", "error");
      try {
        await api(s ? `prospecting/searches/${s.id}/` : "prospecting/searches/", { method: s ? "PATCH" : "POST", body });
        m.close(); toast(s ? "Búsqueda guardada" : "Búsqueda creada. Tocá «Buscar ahora» para que Claude salga a buscar.", "success"); done();
      } catch (ex) { toast(ex.message, "error"); }
    } }, s ? "Guardar" : "Crear búsqueda")],
  });
}

async function runsModal(s) {
  const body = h("div", spinner());
  modal({ title: `Historial de «${s.name}»`, width: "760px", body });
  const runs = (await api("prospecting/runs/", { params: { search: s.id, page_size: 30 } })).results;
  body.replaceChildren(runs.length ? h("div.table-wrap", h("table.grid",
    h("thead", h("tr", ["Fecha", "Estado", "Nuevos", "Búsquedas web", "Costo", "Resumen"].map((x) => h("th.no-sort", x)))),
    h("tbody", runs.map((r) => h("tr",
      h("td.nowrap", datetime(r.created_at)), h("td", badge(r.status, r.status_label)),
      h("td", `${r.new_count} de ${r.found_count}`), h("td", r.web_searches), h("td.nowrap", usd(r.cost_usd)),
      h("td.small", r.error ? h("span", { style: { color: "var(--danger)" } }, r.error) : r.summary || "—"))))))
    : emptyState("Esta búsqueda todavía no se ejecutó."));
}

// ---------- Configuración ----------
async function renderSettingsTab(box, rerender) {
  const cfg = await api("prospecting/settings/");
  const key = h("input.input", { type: "password", autocomplete: "off", placeholder: cfg.has_api_key ? "Pegá una clave nueva para reemplazarla" : "sk-ant-…" });
  const model = h("select.select", cfg.models.map((o) => h("option", { value: o.value, selected: o.value === cfg.model }, o.label)));
  const budget = h("input.input", { type: "number", min: 0, step: 1, value: Number(cfg.monthly_budget_usd) });
  const save = async (extra = {}) => {
    try {
      await api("prospecting/settings/", { method: "PUT", body: { model: model.value, monthly_budget_usd: budget.value || 0, ...extra } });
      toast("Configuración guardada", "success"); rerender();
    } catch (ex) { toast(ex.message, "error"); }
  };
  const test = async (btn) => {
    btn.disabled = true;
    try {
      const r = await api("prospecting/settings/test/", { method: "POST", body: { api_key: key.value.trim(), model: model.value } });
      toast(`La clave funciona (${r.model})`, "success");
    } catch (ex) { toast(ex.message, "error"); }
    btn.disabled = false;
  };
  const testBtn = h("button.btn", { onclick: () => test(testBtn) }, "Probar clave");
  box.append(
    h("section.card", h("div.card-header", icon("key"), h("h3", "Clave de la API de Anthropic"),
      h("span.grow"), cfg.has_api_key ? badge("CALIFICADO", `Cargada ${cfg.api_key_hint}`) : badge("DESCARTADO", "Falta cargar")),
      h("div.card-body.stack",
        h("div.field", h("label", "Clave"), h("div.stack", { style: { gap: "8px" } }, key,
          h("div.row", { style: { flexWrap: "wrap" } },
            h("button.btn.btn-primary", { onclick: () => key.value.trim() ? save({ api_key: key.value.trim() }) : toast("Pegá la clave primero.", "error") }, "Guardar clave"),
            testBtn,
            cfg.has_api_key && !cfg.api_key_from_server ? h("button.btn.btn-ghost", { onclick: async () => {
              if (await confirmDialog("Quitar la clave", "Claude no va a poder buscar hasta que cargues otra.", { okLabel: "Quitar" })) save({ clear_api_key: true });
            } }, "Quitar clave") : null),
          h("span.muted.small", "Se guarda en el servidor y nunca se vuelve a mostrar completa."))),
        h("div.steps", h("strong", "Cómo sacar la clave (una sola vez):"), h("ol",
          h("li", "Entrá a ", ext("https://console.anthropic.com", "console.anthropic.com"), " y creá una cuenta (o ingresá con la tuya)."),
          h("li", "En «Billing» cargá crédito, por ejemplo US$ 20. Se descuenta solo lo que se usa."),
          h("li", "En «API Keys» tocá «Create Key», ponele de nombre «Solvis CRM» y copiala."),
          h("li", "Pegala arriba, tocá «Guardar clave» y después «Probar clave»."))))),
    h("section.card", { style: { marginTop: "14px" } }, h("div.card-header", icon("chart"), h("h3", "Modelo y gasto")),
      h("div.card-body.stack",
        h("div.field", h("label", "Modelo de Claude"), model),
        h("div.field", h("label", "Tope de gasto por mes (US$)"), h("div.stack", { style: { gap: "4px" } }, budget,
          h("span.muted.small", `Este mes van ${usd(cfg.month_spend_usd)}. Al llegar al tope no se lanzan más búsquedas hasta el mes siguiente.`))),
        h("p.muted.small", { style: { margin: 0 } }, "Cada búsqueda muestra su costo estimado en el historial. A más profundidad, más búsquedas en internet y más costo."),
        h("div.row", h("button.btn.btn-primary", { onclick: () => save() }, "Guardar")))),
  );
}
