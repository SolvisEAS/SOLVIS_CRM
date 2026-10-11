// Detalle de un registro: cabecera con acciones, información y listas relacionadas.
import { api } from "/shared/api.js";
import { displayValue } from "../fields.js";
import { icon } from "../icons.js";
import { MODULES, forgetRecent, getStages, recordTitle, rememberRecent } from "../modules.js";
import { whatsappUrl } from "../fields.js";
import { avatar, confirmDialog, datetime, emptyState, h, modal, money, popover, toast } from "../ui.js";
import { openTaskModal, taskRow } from "./tasks.js";

export async function renderDetail(page, mod, id) {
  const record = await api(`${mod.endpoint}/${id}/`);
  const title = recordTitle(mod, record);
  document.title = `${title} · Solvis CRM`;
  rememberRecent(mod, record);
  const reload = () => { page.replaceChildren(); return renderDetail(page, mod, id); };

  // ---- Cabecera ----
  const moreBtn = h("button.btn.btn-icon", { title: "Más acciones", onclick: () => popover(moreBtn, [
    h("button.item", { onclick: () => openTaskModal({ preset: { related_type: mod.relatedType, related_id: record.id }, onSaved: reload }) }, icon("task"), "Nueva tarea"),
    h("button.item", { onclick: () => {
      // Clonar (como en Zoho): abre el formulario con los mismos datos.
      try { sessionStorage.setItem("solvis_crm_clone", JSON.stringify({ path: mod.path, record })); } catch {}
      location.hash = `#/${mod.path}/new?clone=1`;
    } }, icon("copy"), "Clonar"),
    h("div.sep"),
    h("button.item", { style: { color: "var(--danger)" }, onclick: remove }, icon("trash"), "Eliminar"),
  ], { align: "right" }) }, icon("more"));
  const converted = mod.endpoint === "leads" && record.status === "CONVERTIDO";
  const header = h("div.card.record-header",
    h("a.btn.btn-ghost.btn-icon", { href: `#/${mod.path}`, title: `Volver a ${mod.plural}` }, icon("back")),
    avatar(title, "lg"),
    h("div",
      h("div.muted.small", mod.singular.toUpperCase()),
      h("h1", title),
      h("div.muted", mod.subtitle(record) || "")),
    h("div.actions",
      record.phone ? h("a.btn.btn-wa", { href: whatsappUrl(record.phone), target: "_blank", rel: "noopener", title: `WhatsApp ${record.phone}` }, icon("whatsapp"), "WhatsApp") : null,
      record.email ? h("a.btn", { href: `mailto:${record.email}`, title: record.email }, icon("mail"), "Correo") : null,
      mod.endpoint === "leads" && !converted ? h("button.btn.btn-primary", { onclick: () => convertLead(record) }, icon("convert"), "Convertir") : null,
      h("a.btn", { href: `#/${mod.path}/${record.id}/edit` }, icon("edit"), "Editar"),
      moreBtn));

  async function remove() {
    const warning = mod.endpoint === "companies"
      ? `¿Eliminar "${title}"? También se eliminan sus ${record.contacts_count} contactos y ${record.opportunities_count} oportunidades. Esta acción no se puede deshacer.`
      : `¿Eliminar "${title}"? Esta acción no se puede deshacer.`;
    if (!(await confirmDialog(`Eliminar ${mod.singular.toLowerCase()}`, warning))) return;
    try {
      await api(`${mod.endpoint}/${record.id}/`, { method: "DELETE" });
      forgetRecent(mod.path, record.id);
      toast(`${mod.singular} ${mod.gender === "f" ? "eliminada" : "eliminado"}`, "success");
      location.hash = `#/${mod.path}`;
    } catch (ex) { toast(ex.message, "error"); }
  }

  // ---- Barra de etapas (solo oportunidades) ----
  let stagePath = null;
  if (mod.endpoint === "opportunities") {
    const stages = (await getStages()).filter((s) => s.is_active);
    const current = stages.find((s) => s.id === record.stage);
    stagePath = h("div.stage-path", stages.map((s) => {
      const cls = s.id === record.stage ? (s.is_won ? "won" : s.is_lost ? "lost" : "current") : (current && s.sequence < current.sequence && !s.is_lost ? "done" : "");
      return h(`button.stage-step${cls ? "." + cls : ""}`, { title: `Mover a ${s.name}`, onclick: async () => {
        if (s.id === record.stage) return;
        await api(`opportunities/${record.id}/`, { method: "PATCH", body: { stage: s.id, probability: s.probability } });
        toast(`Etapa: ${s.name}`, "success"); reload();
      } }, s.name);
    }));
  }

  // ---- Información ----
  const infoSections = [];
  for (const section of mod.sections) {
    const items = await Promise.all(section.fields.map(async (f) =>
      h(`div.detail-item${f.full ? ".full" : ""}`, h("div.k", f.label), h("div.v", (await displayValue(f, record)) || h("span.muted", "—")))));
    infoSections.push(h("section.card", { id: `sec-${section.title}` }, h("div.card-header", h("h3", section.title)), h("div.card-body", h("div.details", items))));
  }
  const system = h("section.card", h("div.card-header", h("h3", "Información del sistema")), h("div.card-body", h("div.details",
    h("div.detail-item", h("div.k", "Creado"), h("div.v", datetime(record.created_at))),
    h("div.detail-item", h("div.k", "Modificado"), h("div.v", datetime(record.updated_at))),
    record.expected_revenue !== undefined ? h("div.detail-item", h("div.k", "Ingreso esperado"), h("div.v", money(record.expected_revenue), h("span.muted.small", ` (monto × ${record.probability}%)`))) : null,
    record.closed_at ? h("div.detail-item", h("div.k", "Cerrada"), h("div.v", datetime(record.closed_at))) : null)));
  if (converted) {
    infoSections.unshift(h("section.card", { style: { borderColor: "var(--accent)" } }, h("div.card-body.row",
      icon("convert"), h("strong", "Lead convertido"), h("span.muted", datetime(record.converted_at)), h("span.grow"),
      record.converted_company ? h("a.btn.btn-sm", { href: `#/companies/${record.converted_company}` }, "Ver empresa") : null,
      record.converted_contact ? h("a.btn.btn-sm", { href: `#/contacts/${record.converted_contact}` }, "Ver contacto") : null,
      record.converted_opportunity ? h("a.btn.btn-sm", { href: `#/deals/${record.converted_opportunity}` }, "Ver oportunidad") : null)));
  }

  // ---- Listas relacionadas ----
  const relatedCards = [];
  const nav = h("nav.card.related-nav", h("div.title", "Información"),
    mod.sections.map((s) => h("a", { href: "#", onclick: (e) => { e.preventDefault(); document.getElementById(`sec-${s.title}`)?.scrollIntoView({ behavior: "smooth", block: "center" }); } }, icon("note"), s.title)),
    h("div.title", "Listas relacionadas"));
  for (const rel of mod.related) {
    const { card, count, label, ic } = await relatedList(rel, mod, record, reload);
    const anchor = `rel-${rel}`;
    card.id = anchor;
    relatedCards.push(card);
    nav.append(h("a", { href: "#", onclick: (e) => { e.preventDefault(); document.getElementById(anchor)?.scrollIntoView({ behavior: "smooth", block: "start" }); } }, icon(ic), label, h("span.count", count)));
  }

  page.append(...[header, stagePath].filter(Boolean), h("div.record-layout", nav, h("div.stack", infoSections, relatedCards, system)));

  async function convertLead(lead) {
    const stages = (await getStages()).filter((s) => s.is_active && !s.is_won && !s.is_lost);
    const createOpp = h("input.checkbox", { type: "checkbox", checked: true });
    const oppName = h("input.input", { value: lead.title });
    const amount = h("input.input", { type: "number", min: 0, value: 0 });
    const closeDate = h("input.input", { type: "date" });
    const stage = h("select.select", stages.map((s) => h("option", { value: s.id }, s.name)));
    const oppFields = h("div.stack", h("div.field", h("label", "Nombre"), oppName), h("div.field", h("label", "Monto"), amount),
      h("div.field", h("label", "Etapa"), stage), h("div.field", h("label", "Fecha de cierre"), closeDate));
    createOpp.addEventListener("change", () => oppFields.classList.toggle("hidden", !createOpp.checked));
    const m = modal({
      title: `Convertir lead: ${lead.name}`,
      body: [
        h("p.muted", { style: { margin: 0 } }, `Se crea la empresa "${lead.company || lead.name}" (o se usa la existente) y el contacto ${lead.name}.`),
        h("label.row", createOpp, "Crear también una oportunidad"),
        oppFields,
      ],
      footer: [
        h("button.btn", { onclick: () => m.close() }, "Cancelar"),
        h("button.btn.btn-primary", { onclick: async () => {
          try {
            const res = await api(`leads/${lead.id}/convert/`, { method: "POST", body: {
              create_opportunity: createOpp.checked, opportunity_name: oppName.value, amount: amount.value || 0,
              expected_closing_date: closeDate.value || null, stage: Number(stage.value) || null,
            } });
            m.close(); toast("Lead convertido", "success");
            location.hash = res.opportunity ? `#/deals/${res.opportunity}` : `#/contacts/${res.contact}`;
          } catch (ex) { toast(ex.message, "error"); }
        } }, "Convertir"),
      ],
    });
  }
}

async function relatedList(rel, mod, record, reload) {
  if (rel === "notes") return notesCard(mod, record);
  if (rel === "timeline") {
    const data = await api("timeline/", { params: { related_type: mod.relatedType, related_id: record.id, page_size: 100 } });
    const card = h("section.card",
      h("div.card-header", icon("history"), h("h3", "Historial"), h("span.muted", `(${data.count})`)),
      data.results.length ? h("ul.timeline", data.results.map((e) => h(`li.${e.verb}`,
        h("div", e.description), h("div.when", `${e.user_name} · ${datetime(e.created_at)}`)))) : emptyState("Sin movimientos todavía.", "history"));
    return { card, count: data.count, label: "Historial", ic: "history" };
  }
  if (rel === "tasks") {
    const data = await api("tasks/", { params: { related_type: mod.relatedType, related_id: record.id, page_size: 50 } });
    const card = h("section.card",
      h("div.card-header", icon("task"), h("h3", "Tareas"), h("span.muted", `(${data.count})`),
        h("button.btn.btn-sm", { style: { marginLeft: "auto" }, onclick: () => openTaskModal({ preset: { related_type: mod.relatedType, related_id: record.id }, onSaved: reload }) }, icon("plus"), "Nueva tarea")),
      data.results.length ? h("ul.mini-list", data.results.map((t) => taskRow(t, reload))) : emptyState("Sin tareas.", "task"));
    return { card, count: data.count, label: "Tareas", ic: "task" };
  }
  // contactos u oportunidades de esta empresa / contacto
  const target = MODULES[rel];
  const filterKey = mod.endpoint === "companies" ? "company" : "contact";
  const data = await api(`${target.endpoint}/`, { params: { [filterKey]: record.id, page_size: 50 } });
  const presetQuery = `${filterKey}=${record.id}&${filterKey}_label=${encodeURIComponent(recordTitle(mod, record))}` +
    (mod.endpoint === "contacts" && record.company ? `&company=${record.company}&company_label=${encodeURIComponent(record.company_name || "")}` : "");
  const rows = data.results.map((r) => h("li",
    h("div.grow", h("a.title", { href: `#/${target.path}/${r.id}` }, recordTitle(target, r)), h("div.muted.small", target.subtitle(r))),
    rel === "opportunities" ? h("div", { style: { textAlign: "right" } }, h("strong", money(r.amount)), h("div.muted.small", r.stage_name)) : h("span.muted.small", r.email || r.phone || "")));
  const card = h("section.card",
    h("div.card-header", icon(target.icon), h("h3", target.plural), h("span.muted", `(${data.count})`),
      h("a.btn.btn-sm", { style: { marginLeft: "auto" }, href: `#/${target.path}/new?${presetQuery}` }, icon("plus"), `${target.gender === "f" ? "Nueva" : "Nuevo"}`)),
    rows.length ? h("ul.mini-list", rows) : emptyState(`Sin ${target.plural.toLowerCase()}.`, target.icon));
  return { card, count: data.count, label: target.plural, ic: target.icon };
}

async function notesCard(mod, record) {
  const params = { related_type: mod.relatedType, related_id: record.id, page_size: 100 };
  const list = h("div");
  const countEl = h("span.muted");
  const draw = async () => {
    const data = await api("notes/", { params });
    countEl.textContent = `(${data.count})`;
    list.replaceChildren(...(data.results.length ? data.results.map((n) => h("div.note",
      h("div.meta.row", h("strong", n.author_name || ""), h("span", datetime(n.created_at)), h("span.grow"),
        h("button.btn.btn-ghost.btn-sm", { title: "Eliminar nota", onclick: async () => {
          if (!(await confirmDialog("Eliminar nota", "¿Eliminar esta nota?"))) return;
          await api(`notes/${n.id}/`, { method: "DELETE" }); draw();
        } }, icon("trash"))),
      h("div.body", n.body))) : [h("div.muted.small", "Todavía no hay notas.")]));
    return data.count;
  };
  const text = h("textarea.textarea", { placeholder: "Agregar una nota…", rows: 3, style: { minHeight: "70px" } });
  const composer = h("div.notes-composer", text, h("div.row", h("span.grow"),
    h("button.btn.btn-primary.btn-sm", { onclick: async () => {
      if (!text.value.trim()) return;
      await api("notes/", { method: "POST", body: { ...params, page_size: undefined, body: text.value.trim() } });
      text.value = ""; draw();
    } }, "Guardar nota")));
  const count = await draw();
  const card = h("section.card", h("div.card-header", icon("note"), h("h3", "Notas"), countEl), h("div.card-body", composer, list));
  return { card, count, label: "Notas", ic: "note" };
}
