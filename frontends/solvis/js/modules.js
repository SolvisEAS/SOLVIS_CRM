/*
 * Definición de los módulos del CRM (como los módulos de Zoho CRM).
 * Las vistas de lista, detalle y formulario se arman a partir de acá,
 * así que agregar un campo o una columna es tocar solo este archivo.
 *
 * Tipos de campo: text, email, phone, url, textarea, number, money, date,
 * choice (opciones de /api/meta/), user (usuarios del cliente),
 * lookup (otro módulo), stage (etapas del pipeline).
 */
import { api } from "/shared/api.js";

export const MODULES = {
  leads: {
    endpoint: "leads", path: "leads", icon: "lead",
    singular: "Lead", plural: "Leads", gender: "m",
    title: (r) => r.name, subtitle: (r) => [r.title, r.company].filter(Boolean).join(" · "),
    sections: [
      { title: "Información del lead", fields: [
        { name: "name", label: "Nombre del contacto", type: "text", required: true },
        { name: "title", label: "Título del lead", type: "text", required: true },
        { name: "company", label: "Empresa", type: "text" },
        { name: "email", label: "Correo", type: "email" },
        { name: "phone", label: "Teléfono", type: "phone" },
        { name: "source", label: "Origen", type: "choice", choices: "lead_source" },
        { name: "status", label: "Estado", type: "choice", choices: "lead_status", default: "NUEVO" },
        { name: "assigned_to", label: "Propietario", type: "user", display: "assigned_to_username" },
      ] },
      { title: "Descripción", fields: [
        { name: "description", label: "Descripción", type: "textarea", full: true },
      ] },
    ],
    columns: [
      { name: "name", label: "Nombre", link: true, sort: "name" },
      { name: "title", label: "Título" },
      { name: "company", label: "Empresa", sort: "company" },
      { name: "email", label: "Correo" },
      { name: "phone", label: "Teléfono" },
      { name: "source", label: "Origen", type: "choice", choices: "lead_source" },
      { name: "status", label: "Estado", type: "badge", choices: "lead_status", sort: "status" },
      { name: "assigned_to_username", label: "Propietario" },
      { name: "created_at", label: "Creado", type: "date", sort: "created_at" },
    ],
    filters: [
      { name: "status", label: "Estado", choices: "lead_status" },
      { name: "source", label: "Origen", choices: "lead_source" },
      { name: "assigned_to", label: "Propietario", users: true },
    ],
    related: ["notes", "tasks"],
    relatedType: "lead",
  },
  contacts: {
    endpoint: "contacts", path: "contacts", icon: "contact",
    singular: "Contacto", plural: "Contactos", gender: "m",
    title: (r) => `${r.first_name} ${r.last_name}`.trim(), subtitle: (r) => [r.position, r.company_name].filter(Boolean).join(" · "),
    sections: [
      { title: "Información del contacto", fields: [
        { name: "first_name", label: "Nombre", type: "text", required: true },
        { name: "last_name", label: "Apellido", type: "text", required: true },
        { name: "company", label: "Empresa", type: "lookup", module: "companies", display: "company_name" },
        { name: "position", label: "Cargo", type: "text" },
        { name: "email", label: "Correo", type: "email" },
        { name: "phone", label: "Teléfono", type: "phone" },
        { name: "owner", label: "Propietario", type: "user", display: "owner_username" },
      ] },
    ],
    columns: [
      { name: "_title", label: "Nombre", link: true, sort: "last_name" },
      { name: "company_name", label: "Empresa", lookup: { module: "companies", id: "company" } },
      { name: "position", label: "Cargo" },
      { name: "email", label: "Correo" },
      { name: "phone", label: "Teléfono" },
      { name: "owner_username", label: "Propietario" },
      { name: "created_at", label: "Creado", type: "date", sort: "created_at" },
    ],
    filters: [{ name: "owner", label: "Propietario", users: true }],
    related: ["opportunities", "notes", "tasks"],
    relatedType: "contact",
  },
  companies: {
    endpoint: "companies", path: "companies", icon: "company",
    singular: "Empresa", plural: "Empresas", gender: "f",
    title: (r) => r.name, subtitle: (r) => [r.city, r.country].filter(Boolean).join(", "),
    sections: [
      { title: "Información de la empresa", fields: [
        { name: "name", label: "Nombre de la empresa", type: "text", required: true },
        { name: "phone", label: "Teléfono", type: "phone" },
        { name: "email", label: "Correo", type: "email" },
        { name: "website", label: "Sitio web", type: "url" },
        { name: "owner", label: "Propietario", type: "user", display: "owner_username" },
      ] },
      { title: "Dirección", fields: [
        { name: "address", label: "Dirección", type: "text" },
        { name: "city", label: "Ciudad", type: "text" },
        { name: "country", label: "País", type: "text", default: "Paraguay" },
      ] },
    ],
    columns: [
      { name: "name", label: "Empresa", link: true, sort: "name" },
      { name: "phone", label: "Teléfono" },
      { name: "website", label: "Sitio web", type: "url" },
      { name: "city", label: "Ciudad", sort: "city" },
      { name: "contacts_count", label: "Contactos", type: "number" },
      { name: "opportunities_count", label: "Oportunidades", type: "number" },
      { name: "owner_username", label: "Propietario" },
    ],
    filters: [{ name: "owner", label: "Propietario", users: true }],
    related: ["contacts", "opportunities", "notes", "tasks"],
    relatedType: "company",
  },
  opportunities: {
    endpoint: "opportunities", path: "deals", icon: "deal",
    singular: "Oportunidad", plural: "Oportunidades", gender: "f",
    title: (r) => r.name, subtitle: (r) => [r.company_name, r.contact_name].filter(Boolean).join(" · "),
    sections: [
      { title: "Información de la oportunidad", fields: [
        { name: "name", label: "Nombre de la oportunidad", type: "text", required: true },
        { name: "company", label: "Empresa", type: "lookup", module: "companies", display: "company_name", required: true },
        { name: "contact", label: "Contacto", type: "lookup", module: "contacts", display: "contact_name" },
        { name: "amount", label: "Monto", type: "money" },
        { name: "stage", label: "Etapa", type: "stage", display: "stage_name", required: true },
        { name: "probability", label: "Probabilidad (%)", type: "number", min: 0, max: 100 },
        { name: "expected_closing_date", label: "Fecha de cierre", type: "date" },
        { name: "assigned_to", label: "Propietario", type: "user", display: "assigned_to_username" },
      ] },
      { title: "Descripción", fields: [
        { name: "description", label: "Descripción", type: "textarea", full: true },
      ] },
    ],
    columns: [
      { name: "name", label: "Oportunidad", link: true, sort: "name" },
      { name: "company_name", label: "Empresa", lookup: { module: "companies", id: "company" } },
      { name: "amount", label: "Monto", type: "money", sort: "amount" },
      { name: "stage_name", label: "Etapa", type: "stage" },
      { name: "probability", label: "Prob.", type: "percent" },
      { name: "expected_closing_date", label: "Cierre", type: "date", sort: "expected_closing_date" },
      { name: "contact_name", label: "Contacto", lookup: { module: "contacts", id: "contact" } },
      { name: "assigned_to_username", label: "Propietario" },
    ],
    filters: [
      { name: "stage", label: "Etapa", stages: true },
      { name: "assigned_to", label: "Propietario", users: true },
    ],
    related: ["notes", "tasks"],
    relatedType: "opportunity",
    kanban: true,
  },
};

export const byPath = (path) => Object.values(MODULES).find((m) => m.path === path);
export const byRelatedType = (t) => Object.values(MODULES).find((m) => m.relatedType === t);
export const recordTitle = (mod, r) => (r ? mod.title(r) : "");

// ---------- Catálogos compartidos (se piden una vez) ----------
let metaP, usersP, stagesP;
export const getMeta = () => (metaP ||= api("meta/"));
export const getUsers = () => (usersP ||= api("users/", { params: { page_size: 200 } }).then((d) => d.results));
export const getStages = (fresh = false) => {
  if (fresh) stagesP = null;
  return (stagesP ||= api("pipeline-stages/", { params: { ordering: "sequence" } }));
};
export async function choiceLabel(key, value) {
  const meta = await getMeta();
  return meta[key]?.find((c) => c.value === value)?.label || value;
}
export function resetCaches() { metaP = usersP = stagesP = null; }
