// Configuración (como el "Setup" de Zoho): inicio con accesos, usuarios, pipeline y empresa.
import { api, refreshMe, session } from "/shared/api.js";
import { icon } from "../icons.js";
import { getMeta, getStages, resetCaches } from "../modules.js";
import { avatar, badge, confirmDialog, datetime, emptyState, h, modal, popover, toast } from "../ui.js";
import { passwordModal } from "./backoffice.js";

const SECTIONS = {
  company: { title: "Información de la empresa", icon: "company", desc: "Nombre, moneda, colores y logo de tu empresa en el CRM." },
  users: { title: "Usuarios", icon: "users", desc: "Quiénes usan el CRM y con qué rol: administrador, gerente, vendedor o usuario." },
  stages: { title: "Pipeline de ventas", icon: "kanban", desc: "Las etapas por las que pasa una oportunidad, su orden, probabilidad y color." },
};

export async function renderSettings(page, tab) {
  document.title = "Configuración · Solvis CRM";
  const isAdmin = session.user?.role === "ADMINISTRADOR";
  const rerender = () => { page.replaceChildren(); return renderSettings(page, tab); };

  if (!SECTIONS[tab]) {
    page.append(
      h("div.page-header", h("div", h("h1", "Configuración"), h("div.muted", `Ajustes de ${session.tenant?.name || "tu empresa"}`))),
      h("div.settings-home", Object.entries(SECTIONS).map(([key, s]) => h("a.card.settings-card", { href: `#/settings/${key}` },
        h("div.kpi-icon", icon(s.icon)), h("div", h("h3", s.title), h("div.muted", s.desc)))),
        // Solo el personal de Solvis (is_staff) ve el panel donde se crean clientes nuevos.
        session.user?.is_staff ? h("a.card.settings-card", { href: "#/settings/tenants" },
          h("div.kpi-icon", icon("company")), h("div", h("h3", "Clientes"), h("div.muted", "Solo para Solvis: empresas habilitadas, sus usuarios, contraseñas y accesos."))) : null));
    return;
  }

  const sec = SECTIONS[tab];
  const head = (...actions) => h("div.page-header", h("div", h("h1", sec.title), h("div.muted", sec.desc)), h("div.grow"), actions);
  const readOnlyNote = isAdmin ? "" : h("div.card", { style: { padding: "12px 16px", marginBottom: "14px" } }, h("span.muted", "Solo un administrador puede hacer cambios acá."));

  if (tab === "company") {
    const t = await api("tenant/");
    const meta = { currencies: [["PYG", "Guaraní (Gs.)"], ["USD", "Dólar (US$)"], ["BRL", "Real (R$)"], ["ARS", "Peso argentino ($)"]] };
    const name = h("input.input", { value: t.name, disabled: !isAdmin });
    const currency = h("select.select", { disabled: !isAdmin }, meta.currencies.map(([v, l]) => h("option", { value: v, selected: v === t.currency }, l)));
    const colorInput = (value) => {
      const picker = h("input", { type: "color", value: value || "#7B3FE4", disabled: !isAdmin });
      const text = h("input.input", { value: value || "", placeholder: "#RRGGBB", disabled: !isAdmin });
      picker.addEventListener("input", () => { text.value = picker.value.toUpperCase(); preview(); });
      text.addEventListener("input", () => { if (/^#[0-9a-f]{6}$/i.test(text.value)) picker.value = text.value; preview(); });
      return { el: h("div.color-field", picker, text), get: () => text.value.trim() };
    };
    const primary = colorInput(t.primary_color);
    const accent = colorInput(t.accent_color);
    const logo = h("input.input", { value: t.logo_url, placeholder: "https://… (vacío = logo de Solvis)", disabled: !isAdmin });
    const previewBox = h("div.brand-preview");
    function preview() {
      previewBox.style.background = `linear-gradient(90deg, ${primary.get() || "#0E2959"}, #0a1f47)`;
      previewBox.replaceChildren(h("img", { src: logo.value.trim() || "img/isotipo-blanco.png", alt: "", style: { height: "26px" } }),
        h("strong", name.value || "Tu empresa"), h("span.grow"),
        h("span.btn.btn-sm", { style: { background: accent.get() || "#7B3FE4", borderColor: "transparent", color: "#fff" } }, "Botón"));
    }
    [name, logo].forEach((el) => el.addEventListener("input", preview));
    preview();
    const field = (label, control) => h("div.field", h("label", label), h("div", control));
    page.append(
      head(isAdmin ? h("button.btn.btn-primary", { onclick: async () => {
        try {
          await api("tenant/", { method: "PATCH", body: { name: name.value.trim(), currency: currency.value, primary_color: primary.get(), accent_color: accent.get(), logo_url: logo.value.trim() } });
          await refreshMe();
          toast("Información guardada. Recargando colores…", "success");
          setTimeout(() => location.reload(), 900);
        } catch (ex) { toast(ex.message, "error"); }
      } }, "Guardar cambios") : null),
      readOnlyNote,
      h("section.card.form-section", h("div.card-header", h("h3", "Datos generales")), h("div.card-body.stack",
        field("Nombre de la empresa", name), field("Moneda", currency),
        h("div.detail-item", { style: { borderBottom: 0 } }, h("div.k", "Identificador"), h("div.v.muted", `${t.slug} · front "${t.frontend}"`)))),
      h("section.card.form-section", h("div.card-header", h("h3", "Marca")), h("div.card-body.stack",
        field("Color principal", primary.el), field("Color de acento", accent.el), field("Logo (URL)", logo),
        field("Vista previa", previewBox))));
    return;
  }

  if (tab === "stages") {
    const stages = await getStages(true);
    const rows = stages.map((s) => h("tr",
      h("td", h("span.badge", { style: { background: `color-mix(in srgb, ${s.color || "#64748b"} 14%, white)`, color: s.color || "#64748b", borderColor: "transparent" } }, h("span.dot"), s.name)),
      h("td.num", s.sequence), h("td.num", `${s.probability}%`),
      h("td", s.is_won ? "Ganada" : s.is_lost ? "Perdida" : "Abierta"),
      h("td", s.is_active ? "Sí" : "No"),
      h("td", isAdmin ? h("button.btn.btn-sm", { onclick: () => stageModal(s, rerender) }, icon("edit"), "Editar") : "")));
    page.append(
      head(isAdmin ? h("button.btn.btn-primary", { onclick: () => stageModal(null, rerender) }, icon("plus"), "Nueva etapa") : null),
      readOnlyNote,
      h("section.card", stages.length
        ? h("div.table-wrap", h("table.grid", h("thead", h("tr", ["Etapa", "Orden", "Probabilidad", "Tipo", "Activa", ""].map((x, i) => h("th.no-sort", { class: i === 1 || i === 2 ? "num" : "" }, x)))), h("tbody", rows)))
        : emptyState("Todavía no hay etapas.")));
    return;
  }

  // Usuarios
  const [meta, { results: users }] = await Promise.all([getMeta(), api("users/", { params: { page_size: 200 } })]);
  const roleLabel = (r) => meta.user_role.find((c) => c.value === r)?.label || r;
  page.append(
    head(isAdmin ? h("button.btn.btn-primary", { onclick: () => userModal(meta, rerender) }, icon("plus"), "Nuevo usuario") : null),
    readOnlyNote,
    h("section.card", h("div.table-wrap", h("table.grid",
      h("thead", h("tr", ["Usuario", "Correo", "Rol", "Estado", "Último acceso", ""].map((x) => h("th.no-sort", x)))),
      h("tbody", users.map((u) => h("tr",
        h("td", h("div.row", avatar(u.full_name), h("div", h("div.cell-name", u.full_name), h("div.muted.small", u.username)))),
        h("td", u.email || h("span.muted", "—")),
        h("td", badge(u.role, roleLabel(u.role))),
        h("td", u.is_active ? badge("CALIFICADO", "Activo") : badge("DESCARTADO", "Inactivo")),
        h("td", u.last_login ? datetime(u.last_login) : h("span.muted", "Nunca")),
        h("td", { style: { textAlign: "right" } }, isAdmin && u.id !== session.user.id ? userActions(u, meta, rerender) : ""))))))));
}

function userModal(meta, done) {
  const f = Object.fromEntries(["username", "first_name", "last_name", "email"].map((k) => [k, h("input.input")]));
  f.email.type = "email";
  const password = h("input.input", { type: "password", autocomplete: "new-password", minLength: 8 });
  const role = h("select.select", meta.user_role.map((c) => h("option", { value: c.value, selected: c.value === "VENDEDOR" }, c.label)));
  const m = modal({
    title: "Nuevo usuario",
    body: [
      h("div.field.required", h("label", "Usuario"), f.username),
      h("div.field", h("label", "Nombre"), f.first_name), h("div.field", h("label", "Apellido"), f.last_name),
      h("div.field", h("label", "Correo"), f.email),
      h("div.field.required", h("label", "Contraseña"), password),
      h("div.field", h("label", "Rol"), role),
    ],
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async () => {
      try {
        await api("users/", { method: "POST", body: { ...Object.fromEntries(Object.entries(f).map(([k, el]) => [k, el.value.trim()])), password: password.value, role: role.value } });
        m.close(); resetCaches(); toast("Usuario creado", "success"); done();
      } catch (ex) { toast(ex.message, "error"); }
    } }, "Crear usuario")],
  });
}

function stageModal(stage, done) {
  const s = stage || { name: "", sequence: 10, probability: 50, color: "#7B3FE4", is_won: false, is_lost: false, is_active: true };
  const name = h("input.input", { value: s.name });
  const sequence = h("input.input", { type: "number", value: s.sequence });
  const probability = h("input.input", { type: "number", min: 0, max: 100, value: s.probability });
  const color = h("input.input", { type: "color", value: s.color || "#7B3FE4", style: { width: "60px", padding: "2px" } });
  const kind = h("select.select", [["open", "Abierta"], ["won", "Ganada"], ["lost", "Perdida"]].map(([v, l]) =>
    h("option", { value: v, selected: (s.is_won ? "won" : s.is_lost ? "lost" : "open") === v }, l)));
  const active = h("input.checkbox", { type: "checkbox", checked: s.is_active });
  const m = modal({
    title: stage ? "Editar etapa" : "Nueva etapa",
    body: [
      h("div.field.required", h("label", "Nombre"), name), h("div.field", h("label", "Orden"), sequence),
      h("div.field", h("label", "Probabilidad (%)"), probability), h("div.field", h("label", "Color"), color),
      h("div.field", h("label", "Tipo"), kind), h("div.field", h("label", "Activa"), h("div", { style: { paddingTop: "8px" } }, active)),
    ],
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async () => {
      try {
        await api(stage ? `pipeline-stages/${stage.id}/` : "pipeline-stages/", { method: stage ? "PATCH" : "POST", body: {
          name: name.value.trim(), sequence: Number(sequence.value), probability: Number(probability.value), color: color.value,
          is_won: kind.value === "won", is_lost: kind.value === "lost", is_active: active.checked } });
        m.close(); await getStages(true); toast("Etapa guardada", "success"); done();
      } catch (ex) { toast(ex.message, "error"); }
    } }, "Guardar")],
  });
}

// Acciones del administrador del cliente sobre sus usuarios (las mismas del Panel Solvis).
function userActions(u, meta, done) {
  const btn = h("button.btn.btn-sm.btn-icon", { title: "Acciones", onclick: () => popover(btn, [
    h("button.item", { onclick: () => passwordModal(u, "users") }, icon("key"), "Cambiar contraseña"),
    h("button.item", { onclick: async () => {
      try {
        const r = await api(`users/${u.id}/logout/`, { method: "POST" });
        toast(r.sessions_closed ? `Se cerraron las sesiones de ${u.full_name}` : `${u.full_name} no tenía sesiones abiertas`, "success");
      } catch (ex) { toast(ex.message, "error"); }
    } }, icon("logout"), "Cerrar sesión"),
    h("button.item", { onclick: () => roleModal(u, meta, done) }, icon("users"), "Editar datos y rol"),
    h("div.sep"),
    h("button.item", { style: { color: u.is_active ? "var(--danger)" : "var(--success)" }, onclick: async () => {
      if (u.is_active && !(await confirmDialog(`Desactivar a ${u.full_name}`, "No va a poder entrar al CRM y se cierran sus sesiones. Sus registros no se borran.", { okLabel: "Desactivar" }))) return;
      try {
        await api(`users/${u.id}/`, { method: "PATCH", body: { is_active: !u.is_active } });
        toast(u.is_active ? "Usuario desactivado" : "Usuario activado", "success"); done();
      } catch (ex) { toast(ex.message, "error"); }
    } }, icon(u.is_active ? "close" : "check"), u.is_active ? "Desactivar" : "Activar"),
  ], { align: "right" }) }, icon("more"));
  return btn;
}

function roleModal(u, meta, done) {
  const f = Object.fromEntries(["first_name", "last_name", "email"].map((k) => [k, h("input.input", { value: u[k] || "" })]));
  const role = h("select.select", meta.user_role.map((c) => h("option", { value: c.value, selected: c.value === u.role }, c.label)));
  const m = modal({
    title: `Editar ${u.full_name}`,
    body: [h("div.field", h("label", "Nombre"), f.first_name), h("div.field", h("label", "Apellido"), f.last_name),
      h("div.field", h("label", "Correo"), f.email), h("div.field", h("label", "Rol"), role)],
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async () => {
      try {
        await api(`users/${u.id}/`, { method: "PATCH", body: { first_name: f.first_name.value.trim(), last_name: f.last_name.value.trim(), email: f.email.value.trim(), role: role.value } });
        m.close(); resetCaches(); toast("Usuario actualizado", "success"); done();
      } catch (ex) { toast(ex.message, "error"); }
    } }, "Guardar")],
  });
}
