// Cómo se muestra y se edita cada tipo de campo.
import { api, session } from "/shared/api.js";
import { icon } from "./icons.js";
import { MODULES, getMeta, getStages, getUsers, recordTitle } from "./modules.js";
import { badge, date, debounce, h, money } from "./ui.js";

/** Enlace de WhatsApp; los números locales de Paraguay (09…) se pasan a +595. */
export function whatsappUrl(phone) {
  let digits = String(phone).replace(/\D/g, "");
  if (digits.startsWith("0")) digits = `595${digits.slice(1)}`;
  return `https://wa.me/${digits}`;
}

/** Valor para mostrar en tablas y en el detalle. */
export async function displayValue(field, record) {
  const meta = await getMeta();
  const v = field.name === "_title" ? null : record[field.name];
  switch (field.type) {
    case "badge": return v ? badge(v, meta[field.choices]?.find((c) => c.value === v)?.label) : "—";
    case "choice": return v ? (meta[field.choices]?.find((c) => c.value === v)?.label || v) : "";
    case "money": return money(v);
    case "percent": return v !== null && v !== undefined ? `${v}%` : "";
    case "date": return date(v);
    case "url": return v ? h("a", { href: v, target: "_blank", rel: "noopener" }, v.replace(/^https?:\/\//, "")) : "";
    case "email": return v ? h("a", { href: `mailto:${v}` }, v) : "";
    case "phone": return v ? h("span.row", { style: { gap: "6px", display: "inline-flex" } },
      h("a", { href: `tel:${v.replace(/\s/g, "")}` }, v),
      h("a.wa-link", { href: whatsappUrl(v), target: "_blank", rel: "noopener", title: "Escribir por WhatsApp" }, icon("whatsapp"))) : "";
    case "stage": {
      const stages = await getStages();
      const s = stages.find((x) => x.id === (record.stage ?? v));
      return s ? badge(s.name, s.name, s.color) : (record.stage_name || "");
    }
    case "user": return record[field.display] || "";
    case "lookup": {
      const id = record[field.name];
      const label = record[field.display];
      return id ? h("a", { href: `#/${MODULES[field.module].path}/${id}` }, label || `#${id}`) : "";
    }
    case "textarea": return v ? h("div", { style: { whiteSpace: "pre-wrap" } }, v) : "";
    default: return v ?? "";
  }
}

/** Control de formulario para un campo. Devuelve { el, get() } */
export async function inputFor(field, record) {
  const value = record ? record[field.name] : field.default ?? "";
  const id = `f_${field.name}`;
  const base = { id, name: field.name, required: !!field.required };
  switch (field.type) {
    case "textarea": {
      const el = h("textarea.textarea", base, value || "");
      return { el, get: () => el.value };
    }
    case "number": case "money": {
      const el = h("input.input", { ...base, type: "number", step: field.type === "money" ? "1" : "1", min: field.min ?? (field.type === "money" ? 0 : undefined), max: field.max, value: value === "" || value === null ? "" : Number(value) });
      return { el, get: () => (el.value === "" ? (field.type === "money" ? "0" : null) : el.value) };
    }
    case "date": {
      const el = h("input.input", { ...base, type: "date", value: value || "" });
      return { el, get: () => el.value || null };
    }
    case "email": case "url": case "phone": case "text": {
      const el = h("input.input", { ...base, type: field.type === "phone" ? "tel" : field.type, value: value || "", placeholder: field.type === "url" ? "https://" : "" });
      return { el, get: () => el.value.trim() };
    }
    case "choice": {
      const meta = await getMeta();
      const el = h("select.select", base, h("option", { value: "" }, "— Ninguno —"),
        meta[field.choices].map((c) => h("option", { value: c.value, selected: c.value === value }, c.label)));
      return { el, get: () => el.value };
    }
    case "user": {
      const users = await getUsers();
      // Al crear se propone a quien está cargando el registro, como en Zoho.
      const current = record ? value : session.user?.id;
      const el = h("select.select", base, h("option", { value: "" }, "— Sin asignar —"),
        users.map((u) => h("option", { value: u.id, selected: u.id === current }, u.full_name)));
      return { el, get: () => (el.value ? Number(el.value) : null) };
    }
    case "stage": {
      const stages = (await getStages()).filter((s) => s.is_active || s.id === value);
      const el = h("select.select", base, stages.map((s) => h("option", { value: s.id, selected: s.id === value, dataset: { probability: s.probability } }, s.name)));
      return { el, get: () => Number(el.value) };
    }
    case "lookup": return lookupInput(field, record, base);
    default: {
      const el = h("input.input", { ...base, value: value || "" });
      return { el, get: () => el.value };
    }
  }
}

/** Buscador de registros de otro módulo (como los campos de búsqueda de Zoho). */
function lookupInput(field, record, base) {
  const mod = MODULES[field.module];
  let selected = record?.[field.name] ? { id: record[field.name], label: record[field.display] } : null;
  const input = h("input.input", { ...base, placeholder: `Buscar ${mod.singular.toLowerCase()}…`, value: selected?.label || "", autocomplete: "off" });
  input.required = false;
  const dd = h("div.dropdown.hidden");
  const wrap = h("div.lookup", input, dd);
  const close = () => dd.classList.add("hidden");
  const search = debounce(async () => {
    const data = await api(`${mod.endpoint}/`, { params: { search: input.value.trim(), page_size: 8 } });
    dd.replaceChildren(
      ...data.results.map((r) => h("button.item", { type: "button", onmousedown: (e) => { e.preventDefault(); selected = { id: r.id, label: recordTitle(mod, r) }; input.value = selected.label; close(); wrap.dispatchEvent(new CustomEvent("change", { detail: r })); } },
        h("div", h("div", recordTitle(mod, r)), h("div.muted.small", mod.subtitle(r))))),
      data.results.length ? null : h("div.head.muted", "Sin resultados"),
    );
    dd.classList.remove("hidden");
  }, 200);
  input.addEventListener("input", () => { selected = null; search(); });
  input.addEventListener("focus", search);
  input.addEventListener("blur", () => setTimeout(close, 150));
  return {
    el: wrap,
    get: () => (selected ? selected.id : null),
    validate: () => (!field.required || selected ? "" : `Elegí ${mod.gender === "f" ? "una" : "un"} ${mod.singular.toLowerCase()} de la lista.`),
    set: (id, label) => { selected = id ? { id, label } : null; input.value = label || ""; },
  };
}
