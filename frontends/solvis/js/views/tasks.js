// Actividades: lista de tareas, alta/edición en un modal y fila reutilizable.
import { api, session } from "/shared/api.js";
import { icon } from "../icons.js";
import { byRelatedType, getMeta, getUsers } from "../modules.js";
import { badge, confirmDialog, emptyState, h, modal, relDays, spinner, toast } from "../ui.js";

const label = (meta, key, v) => meta[key]?.find((c) => c.value === v)?.label || v;

export async function renderTasks(page, query) {
  document.title = "Actividades · Solvis CRM";
  const meta = await getMeta();
  const state = { status: query.get("status") ?? "open", mine: query.get("mine") !== "0" };
  const listBox = h("div");
  const tabs = h("div.btn-group");
  const drawTabs = () => tabs.replaceChildren(
    ...[["open", "Abiertas"], ["COMPLETADA", "Completadas"], ["", "Todas"]].map(([v, l]) =>
      h(`button.btn${state.status === v ? ".active" : ""}`, { onclick: () => { state.status = v; drawTabs(); load(); } }, l)));
  const mineBox = h("input.checkbox", { type: "checkbox", checked: state.mine, onchange: (e) => { state.mine = e.target.checked; load(); } });
  drawTabs();
  page.append(
    h("div.page-header", h("h1", "Actividades"), h("div.grow"),
      h("label.row", mineBox, "Solo mis tareas"), tabs,
      h("button.btn.btn-primary", { onclick: () => openTaskModal({ onSaved: load }) }, icon("plus"), "Nueva tarea")),
    h("section.card", listBox));

  async function load() {
    listBox.replaceChildren(spinner());
    const params = { page_size: 200, ordering: "due_date" };
    if (state.status && state.status !== "open") params.status = state.status;
    if (state.mine) params.assigned_to = session.user.id;
    let { results } = await api("tasks/", { params });
    if (state.status === "open") results = results.filter((t) => t.status !== "COMPLETADA");
    listBox.replaceChildren(results.length ? h("ul.mini-list", results.map((t) => taskRow(t, load, meta))) : emptyState("No hay tareas acá.", "task"));
  }
  return load();
}

export function taskRow(t, onChange, meta) {
  const done = t.status === "COMPLETADA";
  const overdue = !done && t.due_date && new Date(`${t.due_date}T23:59:59`) < new Date();
  const relMod = t.related_type ? byRelatedType(t.related_type) : null;
  const check = h("input.checkbox", { type: "checkbox", checked: done, title: done ? "Reabrir" : "Marcar como completada", onchange: async (e) => {
    await api(`tasks/${t.id}/`, { method: "PATCH", body: { status: e.target.checked ? "COMPLETADA" : "PENDIENTE" } });
    toast(e.target.checked ? "Tarea completada" : "Tarea reabierta", "success"); onChange?.();
  } });
  const li = h("li", check,
    h("div.grow",
      h("a.title", { href: "#", style: { color: "var(--text)", textDecoration: done ? "line-through" : "none" }, onclick: (e) => { e.preventDefault(); openTaskModal({ task: t, onSaved: onChange }); } }, t.title),
      h("div.small.muted.row", { style: { gap: "10px" } },
        h("span", { style: { color: overdue ? "var(--danger)" : "" } }, t.due_date ? relDays(t.due_date) : "Sin fecha"),
        t.assigned_to_name ? h("span", `· ${t.assigned_to_name}`) : null,
        relMod && t.related_id ? h("a", { href: `#/${relMod.path}/${t.related_id}` }, `· ${relMod.singular}`) : null)),
    t.priority !== "NORMAL" ? badge(t.priority, t.priority === "ALTA" ? "Alta" : "Baja") : null,
    h("button.btn.btn-ghost.btn-sm", { title: "Eliminar", onclick: async () => {
      if (!(await confirmDialog("Eliminar tarea", `¿Eliminar "${t.title}"?`))) return;
      await api(`tasks/${t.id}/`, { method: "DELETE" }); onChange?.();
    } }, icon("trash")));
  return li;
}

export async function openTaskModal({ task, preset = {}, onSaved } = {}) {
  const [meta, users] = await Promise.all([getMeta(), getUsers()]);
  const v = task || { status: "PENDIENTE", priority: "NORMAL", ...preset };
  const title = h("input.input", { value: v.title || "", required: true, placeholder: "Ej: Llamar para confirmar la reunión" });
  const due = h("input.input", { type: "date", value: v.due_date || "" });
  const sel = (key, val) => h("select.select", meta[key].map((c) => h("option", { value: c.value, selected: c.value === val }, c.label)));
  const status = sel("task_status", v.status);
  const priority = sel("task_priority", v.priority);
  const owner = h("select.select", users.map((u) => h("option", { value: u.id, selected: u.id === (v.assigned_to ?? session.user.id) }, u.full_name)));
  const desc = h("textarea.textarea", { rows: 3 }, v.description || "");
  const relMod = v.related_type ? byRelatedType(v.related_type) : null;
  const m = modal({
    title: task ? "Editar tarea" : "Nueva tarea",
    body: [
      h("div.field.required", h("label", "Asunto"), title),
      h("div.field", h("label", "Vence"), due),
      h("div.field", h("label", "Estado"), status),
      h("div.field", h("label", "Prioridad"), priority),
      h("div.field", h("label", "Asignada a"), owner),
      relMod ? h("div.field", h("label", "Relacionada con"), h("div", { style: { paddingTop: "8px" } }, h("a", { href: `#/${relMod.path}/${v.related_id}` }, `${relMod.singular} #${v.related_id}`))) : null,
      h("div.field", h("label", "Descripción"), desc),
    ],
    footer: [
      h("button.btn", { onclick: () => m.close() }, "Cancelar"),
      h("button.btn.btn-primary", { onclick: async () => {
        if (!title.value.trim()) { title.focus(); return toast("Poné un asunto para la tarea.", "error"); }
        const body = { title: title.value.trim(), due_date: due.value || null, status: status.value, priority: priority.value,
          assigned_to: Number(owner.value), description: desc.value, related_type: v.related_type || "", related_id: v.related_id || null };
        await api(task ? `tasks/${task.id}/` : "tasks/", { method: task ? "PATCH" : "POST", body });
        m.close(); toast(task ? "Tarea actualizada" : "Tarea creada", "success"); onSaved?.();
      } }, "Guardar"),
    ],
  });
}
