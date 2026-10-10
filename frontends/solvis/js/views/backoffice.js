// Panel Solvis: clientes a los que se les vende el CRM y sus usuarios (solo personal de Solvis).
import { api, session } from "/shared/api.js";
import { icon } from "../icons.js";
import { getMeta } from "../modules.js";
import { avatar, badge, confirmDialog, datetime, emptyState, h, modal, popover, toast } from "../ui.js";

const FRONTENDS = ["solvis"]; // carpetas disponibles en /frontends (se agregan al crear fronts nuevos)
const statusBadge = (active, on = "Activo", off = "Suspendido") =>
  active ? badge("CALIFICADO", on) : badge("DESCARTADO", off);

export async function renderBackoffice(page, id) {
  if (!session.user?.is_staff) {
    page.append(h("div.card", emptyState("Esta sección es solo para el personal de Solvis.", "close")));
    return;
  }
  return id ? renderTenant(page, Number(id)) : renderTenants(page);
}

async function renderTenants(page) {
  document.title = "Clientes · Solvis CRM";
  const tenants = await api("backoffice/tenants/");
  const rerender = () => { page.replaceChildren(); renderTenants(page); };
  const rows = tenants.map((t) => h("tr",
    h("td", h("div.row", avatar(t.name), h("div", h("a.cell-name", { href: `#/settings/tenants/${t.id}` }, t.name), h("div.muted.small", t.slug)))),
    h("td", statusBadge(t.is_active)),
    h("td.num", `${t.active_users} / ${t.users_count}`),
    h("td.num", t.companies_count), h("td.num", t.leads_count), h("td.num", t.opportunities_count),
    h("td", t.frontend),
    h("td", t.last_login ? datetime(t.last_login) : h("span.muted", "Nunca")),
    h("td", h("a.btn.btn-sm", { href: `#/settings/tenants/${t.id}` }, "Administrar"))));
  const active = tenants.filter((t) => t.is_active).length;
  page.append(
    h("div.page-header", h("div", h("h1", "Clientes"), h("div.muted", "Empresas habilitadas para usar el CRM, sus usuarios y accesos.")), h("div.grow"),
      h("button.btn.btn-primary", { onclick: () => tenantModal(null, (t) => { location.hash = `#/settings/tenants/${t.id}`; }) }, icon("plus"), "Nuevo cliente")),
    h("div.kpis",
      kpi("company", "", "Clientes", tenants.length, `${active} activos`),
      kpi("users", "blue", "Usuarios", tenants.reduce((a, t) => a + t.users_count, 0), "en todos los clientes"),
      kpi("close", "amber", "Suspendidos", tenants.length - active, "sin acceso al CRM")),
    h("section.card", tenants.length ? h("div.table-wrap", h("table.grid",
      h("thead", h("tr", ["Cliente", "Estado", "Usuarios activos", "Empresas", "Leads", "Oportunidades", "Front", "Último acceso", ""].map((x, i) =>
        h("th.no-sort", { class: i >= 2 && i <= 5 ? "num" : "" }, x)))),
      h("tbody", rows))) : emptyState("Todavía no hay clientes.")));
}

function kpi(ic, color, label, value, sub) {
  return h("div.card.kpi", h(`div.kpi-icon${color ? "." + color : ""}`, icon(ic)), h("div", h("div.label", label), h("div.value", value), h("div.sub", sub)));
}

async function renderTenant(page, id) {
  const [t, users, meta] = await Promise.all([api(`backoffice/tenants/${id}/`), api(`backoffice/tenants/${id}/users/`), getMeta()]);
  document.title = `${t.name} · Clientes · Solvis CRM`;
  const rerender = () => { page.replaceChildren(); renderTenant(page, id); };
  const own = session.tenant?.id === t.id;
  const roleLabel = (r) => meta.user_role.find((c) => c.value === r)?.label || r;

  const toggleTenant = async () => {
    if (t.is_active) {
      if (!(await confirmDialog(`Suspender ${t.name}`, "Sus usuarios no van a poder entrar al CRM y se cierran todas sus sesiones. Los datos no se borran y podés reactivarlo cuando quieras.", { okLabel: "Suspender" }))) return;
      const r = await api(`backoffice/tenants/${t.id}/suspend/`, { method: "POST" });
      toast(`Cliente suspendido. Sesiones cerradas: ${r.sessions_closed}`, "success");
    } else {
      await api(`backoffice/tenants/${t.id}/activate/`, { method: "POST" });
      toast("Cliente reactivado", "success");
    }
    rerender();
  };

  const userRows = users.map((u) => {
    const more = h("button.btn.btn-sm.btn-icon", { title: "Acciones", onclick: () => {
      const items = [
        h("button.item", { onclick: () => passwordModal(u) }, icon("edit"), "Cambiar contraseña"),
        h("button.item", { onclick: async () => {
          const r = await api(`backoffice/users/${u.id}/logout/`, { method: "POST" });
          toast(r.sessions_closed ? `Se cerraron ${r.sessions_closed} sesiones de ${u.full_name}` : `${u.full_name} no tenía sesiones abiertas`, "success");
        } }, icon("logout"), "Cerrar sesión"),
        h("button.item", { onclick: () => userModal(t, u, rerender) }, icon("users"), "Editar datos y rol"),
        h("div.sep"),
        h("button.item", { style: { color: u.is_active ? "var(--danger)" : "var(--success)" }, onclick: async () => {
          if (u.is_active && !(await confirmDialog(`Desactivar a ${u.full_name}`, "No va a poder entrar al CRM y se cierran sus sesiones.", { okLabel: "Desactivar" }))) return;
          await api(`backoffice/users/${u.id}/`, { method: "PATCH", body: { is_active: !u.is_active } });
          toast(u.is_active ? "Usuario desactivado" : "Usuario activado", "success"); rerender();
        } }, icon(u.is_active ? "close" : "check"), u.is_active ? "Desactivar usuario" : "Activar usuario"),
      ];
      popover(more, items, { align: "right" });
    } }, icon("more"));
    return h("tr",
      h("td", h("div.row", avatar(u.full_name), h("div", h("div.cell-name", u.full_name, u.is_staff ? h("span.muted.small", " · Solvis") : ""), h("div.muted.small", u.username)))),
      h("td", u.email || h("span.muted", "—")),
      h("td", badge(u.role, roleLabel(u.role))),
      h("td", statusBadge(u.is_active, "Activo", "Inactivo")),
      h("td", u.last_login ? datetime(u.last_login) : h("span.muted", "Nunca")),
      h("td", { style: { textAlign: "right" } }, more));
  });

  page.append(
    h("div.card.record-header",
      h("a.btn.btn-ghost.btn-icon", { href: "#/settings/tenants", title: "Volver a Clientes" }, icon("back")),
      avatar(t.name, "lg"),
      h("div", h("div.muted.small", "CLIENTE"), h("h1", t.name), h("div.row", statusBadge(t.is_active), h("span.muted", `${t.slug} · front "${t.frontend}"`))),
      h("div.actions",
        h("button.btn", { onclick: () => tenantModal(t, rerender) }, icon("edit"), "Editar"),
        own ? null : h(`button.btn${t.is_active ? ".btn-danger" : ".btn-primary"}`, { onclick: toggleTenant }, icon(t.is_active ? "close" : "check"), t.is_active ? "Suspender" : "Reactivar"))),
    h("div.kpis",
      kpi("users", "", "Usuarios activos", `${t.active_users} / ${t.users_count}`, t.last_login ? `Último acceso: ${datetime(t.last_login)}` : "Nadie entró todavía"),
      kpi("company", "blue", "Empresas", t.companies_count, "cargadas en su CRM"),
      kpi("lead", "amber", "Leads", t.leads_count, "cargados en su CRM"),
      kpi("deal", "green", "Oportunidades", t.opportunities_count, "cargadas en su CRM")),
    h("section.card",
      h("div.card-header", icon("users"), h("h3", "Usuarios"), h("span.muted", `(${users.length})`),
        h("button.btn.btn-sm.btn-primary", { style: { marginLeft: "auto" }, onclick: () => userModal(t, null, rerender) }, icon("plus"), "Nuevo usuario")),
      users.length ? h("div.table-wrap", h("table.grid",
        h("thead", h("tr", ["Usuario", "Correo", "Rol", "Estado", "Último acceso", ""].map((x) => h("th.no-sort", x)))),
        h("tbody", userRows))) : emptyState("Este cliente todavía no tiene usuarios. Creá el primero.")));
}

function showPassword(title, user, password) {
  const box = h("input.input", { value: password, readonly: true, style: { fontFamily: "monospace", fontSize: "16px", letterSpacing: ".04em" } });
  const m = modal({
    title,
    body: [
      h("p", { style: { margin: 0 } }, `Usuario: `, h("strong", user)),
      h("div.row", box, h("button.btn", { onclick: async () => {
        try { await navigator.clipboard.writeText(password); toast("Copiada", "success"); } catch { box.select(); }
      } }, "Copiar")),
      h("p.muted.small", { style: { margin: 0 } }, "Pasásela al cliente por un medio seguro. Por seguridad no se vuelve a mostrar: si se pierde, generá otra."),
    ],
    footer: [h("button.btn.btn-primary", { onclick: () => m.close() }, "Listo")],
  });
}

function passwordModal(u) {
  const mode = h("select.select", h("option", { value: "gen" }, "Generar una automáticamente"), h("option", { value: "typed" }, "Escribirla yo"));
  const typed = h("input.input.hidden", { type: "text", placeholder: "Mínimo 8 caracteres", autocomplete: "off" });
  const logout = h("input.checkbox", { type: "checkbox", checked: true });
  mode.addEventListener("change", () => typed.classList.toggle("hidden", mode.value !== "typed"));
  const m = modal({
    title: `Cambiar contraseña de ${u.full_name}`,
    body: [h("div.field", h("label", "Contraseña nueva"), h("div.stack", { style: { gap: "8px" } }, mode, typed)),
      h("label.row", logout, "Cerrar sus sesiones abiertas")],
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async () => {
      try {
        const r = await api(`backoffice/users/${u.id}/set-password/`, { method: "POST", body: { password: mode.value === "typed" ? typed.value : "", logout: logout.checked } });
        m.close();
        r.generated_password ? showPassword("Contraseña nueva", u.username, r.generated_password) : toast("Contraseña cambiada", "success");
      } catch (ex) { toast(ex.message, "error"); }
    } }, "Cambiar contraseña")],
  });
}

async function userModal(tenant, u, done) {
  const meta = await getMeta();
  const f = Object.fromEntries(["username", "first_name", "last_name", "email"].map((k) => [k, h("input.input", { value: u?.[k] || "", disabled: k === "username" && !!u })]));
  f.email.type = "email";
  const role = h("select.select", meta.user_role.map((c) => h("option", { value: c.value, selected: c.value === (u?.role || "ADMINISTRADOR") }, c.label)));
  const m = modal({
    title: u ? `Editar ${u.full_name}` : `Nuevo usuario de ${tenant.name}`,
    body: [
      h("div.field.required", h("label", "Usuario"), f.username),
      h("div.field", h("label", "Nombre"), f.first_name), h("div.field", h("label", "Apellido"), f.last_name),
      h("div.field", h("label", "Correo"), f.email), h("div.field", h("label", "Rol"), role),
      u ? null : h("p.muted.small", { style: { margin: 0 } }, "La contraseña se genera sola y te la muestro al crear el usuario."),
    ],
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async () => {
      const body = { first_name: f.first_name.value.trim(), last_name: f.last_name.value.trim(), email: f.email.value.trim(), role: role.value };
      try {
        if (u) {
          await api(`backoffice/users/${u.id}/`, { method: "PATCH", body });
          m.close(); toast("Usuario actualizado", "success");
        } else {
          if (!f.username.value.trim()) return toast("Poné un nombre de usuario.", "error");
          const r = await api(`backoffice/tenants/${tenant.id}/users/`, { method: "POST", body: { ...body, username: f.username.value.trim() } });
          m.close(); showPassword("Usuario creado", r.username, r.generated_password);
        }
        done();
      } catch (ex) { toast(ex.message, "error"); }
    } }, u ? "Guardar" : "Crear usuario")],
  });
}

function tenantModal(t, done) {
  const name = h("input.input", { value: t?.name || "" });
  const slug = h("input.input", { value: t?.slug || "", disabled: !!t, placeholder: "ej: ferreteria-el-clavo" });
  if (!t) name.addEventListener("input", () => {
    slug.value = name.value.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60);
  });
  const frontend = h("select.select", FRONTENDS.concat(t && !FRONTENDS.includes(t.frontend) ? [t.frontend] : []).map((f) => h("option", { value: f, selected: f === (t?.frontend || "solvis") }, f)));
  const currency = h("select.select", [["PYG", "Guaraní (Gs.)"], ["USD", "Dólar (US$)"], ["BRL", "Real (R$)"], ["ARS", "Peso argentino ($)"]].map(([v, l]) => h("option", { value: v, selected: v === (t?.currency || "PYG") }, l)));
  const primary = h("input.input", { type: "color", value: t?.primary_color || "#0E2959", style: { width: "60px", padding: "2px" } });
  const accent = h("input.input", { type: "color", value: t?.accent_color || "#7B3FE4", style: { width: "60px", padding: "2px" } });
  const m = modal({
    title: t ? `Editar ${t.name}` : "Nuevo cliente",
    body: [
      h("div.field.required", h("label", "Nombre"), name),
      h("div.field.required", h("label", "Identificador"), slug),
      h("div.field", h("label", "Front"), frontend),
      h("div.field", h("label", "Moneda"), currency),
      h("div.field", h("label", "Colores"), h("div.row", primary, accent, h("span.muted.small", "principal y acento"))),
      t ? null : h("p.muted.small", { style: { margin: 0 } }, "Se crea con las etapas de venta por defecto. Después le agregás los usuarios."),
    ],
    footer: [h("button.btn", { onclick: () => m.close() }, "Cancelar"), h("button.btn.btn-primary", { onclick: async () => {
      const body = { name: name.value.trim(), frontend: frontend.value, currency: currency.value, primary_color: primary.value.toUpperCase(), accent_color: accent.value.toUpperCase() };
      if (!t) body.slug = slug.value.trim();
      try {
        const saved = await api(t ? `backoffice/tenants/${t.id}/` : "backoffice/tenants/", { method: t ? "PATCH" : "POST", body });
        m.close(); toast(t ? "Cliente actualizado" : "Cliente creado", "success"); done(saved);
      } catch (ex) { toast(ex.message, "error"); }
    } }, t ? "Guardar" : "Crear cliente")],
  });
}
