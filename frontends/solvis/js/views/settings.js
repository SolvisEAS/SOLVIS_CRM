// Configuración: empresa, usuarios y etapas del pipeline.
import { api, session } from "/shared/api.js";
import { icon } from "../icons.js";
import { getMeta, getStages, resetCaches } from "../modules.js";
import { avatar, badge, h, modal, toast } from "../ui.js";

export async function renderSettings(page, tab = "users") {
  document.title = "Configuración · Solvis CRM";
  const isAdmin = session.user?.role === "ADMINISTRADOR";
  const tabs = [["users", "Usuarios", "users"], ["stages", "Etapas del pipeline", "kanban"], ["company", "Empresa", "company"]];
  const body = h("div");
  page.append(
    h("div.page-header", h("h1", "Configuración")),
    h("div.record-layout",
      h("nav.card.related-nav", h("div.title", "Ajustes"), tabs.map(([k, l, ic]) =>
        h("a", { href: `#/settings/${k}`, style: tab === k ? { background: "var(--accent-soft)", color: "var(--accent)", fontWeight: 600 } : {} }, icon(ic), l))),
      body));

  if (tab === "company") {
    const t = session.tenant || {};
    body.append(h("section.card", h("div.card-header", h("h3", "Empresa")), h("div.card-body", h("div.details",
      ...[["Nombre", t.name], ["Identificador", t.slug], ["Front", t.frontend], ["Moneda", t.currency]].map(([k, v]) =>
        h("div.detail-item", h("div.k", k), h("div.v", v || "—")))))));
    return;
  }

  if (tab === "stages") {
    const stages = await getStages(true);
    const rows = stages.map((s) => h("tr",
      h("td", h("span.badge", { style: { background: `color-mix(in srgb, ${s.color || "#64748b"} 14%, white)`, color: s.color || "#64748b", borderColor: "transparent" } }, h("span.dot"), s.name)),
      h("td.num", s.sequence), h("td.num", `${s.probability}%`),
      h("td", s.is_won ? "Ganada" : s.is_lost ? "Perdida" : "Abierta"),
      h("td", s.is_active ? "Sí" : "No"),
      h("td", isAdmin ? h("button.btn.btn-sm", { onclick: () => stageModal(s) }, icon("edit"), "Editar") : "")));
    body.append(h("section.card",
      h("div.card-header", h("h3", "Etapas del pipeline"), isAdmin ? h("button.btn.btn-sm.btn-primary", { style: { marginLeft: "auto" }, onclick: () => stageModal() }, icon("plus"), "Nueva etapa") : null),
      h("div.table-wrap", h("table.grid", h("thead", h("tr", ["Etapa", "Orden", "Probabilidad", "Tipo", "Activa", ""].map((x) => h("th.no-sort", x)))), h("tbody", rows)))));
    return;
  }

  const [meta, { results: users }] = await Promise.all([getMeta(), api("users/", { params: { page_size: 200 } })]);
  const roleLabel = (r) => meta.user_role.find((c) => c.value === r)?.label || r;
  body.append(h("section.card",
    h("div.card-header", h("h3", "Usuarios"), h("span.muted", `(${users.length})`),
      isAdmin ? h("button.btn.btn-sm.btn-primary", { style: { marginLeft: "auto" }, onclick: () => userModal(meta) }, icon("plus"), "Nuevo usuario") : null),
    h("ul.mini-list", users.map((u) => h("li", avatar(u.full_name), h("div.grow", h("div.title", u.full_name), h("div.muted.small", `${u.username}${u.email ? " · " + u.email : ""}`)),
      badge(u.role, roleLabel(u.role)))))));

  function userModal(meta) {
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
          m.close(); resetCaches(); toast("Usuario creado", "success"); location.hash = "#/settings/users"; renderAgain();
        } catch (ex) { toast(ex.message, "error"); }
      } }, "Crear usuario")],
    });
  }

  function renderAgain() { page.replaceChildren(); renderSettings(page, tab); }
}

function stageModal(stage) {
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
        m.close(); await getStages(true); toast("Etapa guardada", "success");
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      } catch (ex) { toast(ex.message, "error"); }
    } }, "Guardar")],
  });
}
