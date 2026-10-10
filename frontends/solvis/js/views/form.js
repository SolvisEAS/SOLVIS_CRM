// Formulario de creación/edición, con secciones en dos columnas (como Zoho).
import { api } from "/shared/api.js";
import { inputFor } from "../fields.js";
import { getStages, recordTitle } from "../modules.js";
import { h, toast } from "../ui.js";

export async function renderForm(page, mod, id, query) {
  const record = id ? await api(`${mod.endpoint}/${id}/`) : null;
  // Valores que vienen en la URL (ej: crear oportunidad desde una empresa).
  const preset = record ? null : Object.fromEntries([...query.entries()]);
  const title = record ? `Editar ${mod.singular.toLowerCase()}` : `${mod.gender === "f" ? "Nueva" : "Nuevo"} ${mod.singular.toLowerCase()}`;
  document.title = `${title} · Solvis CRM`;

  const controls = {};
  const errors = {};
  const sections = [];
  for (const section of mod.sections) {
    const grid = h("div.form-grid");
    for (const field of section.fields) {
      const seed = record || (preset && field.name in preset ? { [field.name]: castPreset(field, preset[field.name]), [field.display]: preset[`${field.name}_label`] } : null);
      const ctl = await inputFor(field, seed);
      controls[field.name] = ctl;
      errors[field.name] = h("div.field-error");
      grid.append(h(`div.field${field.required ? ".required" : ""}${field.full ? ".full" : ""}`,
        h("label", { for: `f_${field.name}` }, field.label), h("div", ctl.el, errors[field.name])));
    }
    sections.push(h("section.card.form-section", h("div.card-header", h("h3", section.title)), h("div.card-body", grid)));
  }

  // En oportunidades, al cambiar la etapa se sugiere su probabilidad.
  if (controls.stage && controls.probability) {
    const stageSel = controls.stage.el, prob = controls.probability.el;
    if (!record && !prob.value) prob.value = stageSel.selectedOptions[0]?.dataset.probability || "";
    stageSel.addEventListener("change", () => { prob.value = stageSel.selectedOptions[0]?.dataset.probability || prob.value; });
  }
  // Al elegir un contacto se completa su empresa si estaba vacía.
  if (controls.contact && controls.company?.set) {
    controls.contact.el.addEventListener("change", (e) => {
      const c = e.detail;
      if (c?.company && !controls.company.get()) controls.company.set(c.company, c.company_name);
    });
  }

  const back = record ? `#/${mod.path}/${record.id}` : `#/${mod.path}`;
  const save = async (andNew) => {
    Object.values(errors).forEach((e) => (e.textContent = ""));
    let invalid = false;
    for (const section of mod.sections) for (const f of section.fields) {
      const ctl = controls[f.name];
      const msg = ctl.validate ? ctl.validate() : (f.required && (ctl.get() === "" || ctl.get() === null) ? "Este campo es obligatorio." : "");
      if (msg) { errors[f.name].textContent = msg; invalid = true; }
    }
    if (invalid) return toast("Revisá los campos marcados.", "error");
    const body = {};
    for (const [name, ctl] of Object.entries(controls)) body[name] = ctl.get();
    try {
      const saved = await api(record ? `${mod.endpoint}/${record.id}/` : `${mod.endpoint}/`, { method: record ? "PATCH" : "POST", body });
      toast(record ? "Cambios guardados" : `${mod.singular} ${mod.gender === "f" ? "creada" : "creado"}`, "success");
      if (mod.endpoint === "pipeline-stages") getStages(true);
      location.hash = andNew ? `#/${mod.path}/new?_=${Date.now()}` : `#/${mod.path}/${saved.id}`;
    } catch (ex) {
      const data = ex.data || {};
      let shown = false;
      for (const [k, v] of Object.entries(data)) if (errors[k]) { errors[k].textContent = [].concat(v)[0]; shown = true; }
      toast(shown ? "Revisá los campos marcados." : ex.message, "error");
    }
  };

  page.append(h("div.form-page",
    h("div.form-actions",
      h("h1", title, record ? h("span.muted", { style: { fontWeight: 400 } }, ` · ${recordTitle(mod, record)}`) : ""),
      h("a.btn", { href: back }, "Cancelar"),
      record ? null : h("button.btn", { onclick: () => save(true) }, "Guardar y nuevo"),
      h("button.btn.btn-primary", { onclick: () => save(false) }, "Guardar")),
    h("form", { onsubmit: (e) => { e.preventDefault(); save(false); } }, sections, h("button", { type: "submit", hidden: true }))));
}

function castPreset(field, v) {
  return ["lookup", "user", "stage"].includes(field.type) ? Number(v) : v;
}
