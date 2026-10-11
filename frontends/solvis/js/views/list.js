// Vista de lista de un módulo: filtros a la izquierda, tabla y paginación (estilo Zoho).
import { api } from "/shared/api.js";
import { displayValue } from "../fields.js";
import { icon } from "../icons.js";
import { MODULES, getMeta, getStages, getUsers, recordTitle } from "../modules.js";
import { confirmDialog, debounce, emptyState, h, popover, spinner, toast } from "../ui.js";
import { renderKanban } from "./kanban.js";

const PAGE_SIZES = [20, 50, 100];

export async function renderList(page, mod, query) {
  document.title = `${mod.plural} · Solvis CRM`;
  const view = mod.kanban && query.get("view") === "kanban" ? "kanban" : "list";
  const state = {
    page: 1, pageSize: 20, ordering: "", search: query.get("search") || "",
    filters: Object.fromEntries(mod.filters.map((f) => [f.name, query.get(f.name) || ""])),
    selected: new Set(),
  };
  const [meta, users, stages] = await Promise.all([getMeta(), getUsers(), mod.kanban ? getStages() : null]);

  const newLabel = `Crear ${mod.singular.toLowerCase()}`;
  const header = h("div.page-header",
    h("h1", mod.plural), h("span.count", "…"),
    h("div.grow"),
    mod.kanban ? h("div.btn-group",
      h(`a.btn${view === "list" ? ".active" : ""}`, { href: `#/${mod.path}`, title: "Lista" }, icon("list")),
      h(`a.btn${view === "kanban" ? ".active" : ""}`, { href: `#/${mod.path}?view=kanban`, title: "Tablero por etapa" }, icon("kanban"))) : null,
    h("a.btn.btn-primary", { href: `#/${mod.path}/new` }, icon("plus"), newLabel),
  );
  const countEl = header.querySelector(".count");

  // ---- Filtros (columna izquierda) ----
  const searchInput = h("input.input", { type: "search", placeholder: `Buscar ${mod.plural.toLowerCase()}…`, value: state.search });
  const filterOptions = (f) => {
    if (f.users) return users.map((u) => ({ value: String(u.id), label: u.full_name }));
    if (f.stages) return stages.map((s) => ({ value: String(s.id), label: s.name, color: s.color }));
    return meta[f.choices];
  };
  const filterGroups = mod.filters.map((f) => {
    const box = h("div.filter-group", h("h4", f.label));
    const draw = () => box.replaceChildren(h("h4", f.label),
      ...[{ value: "", label: "Todos" }, ...filterOptions(f)].map((o) => h(`button.filter-opt${state.filters[f.name] === o.value ? ".active" : ""}`, {
        type: "button", onclick: () => { state.filters[f.name] = o.value; state.page = 1; draw(); load(); },
      }, h("span.dot", { style: o.color ? { background: o.color } : {} }), o.label)));
    draw();
    return box;
  });
  const groupsBox = h("div.filter-groups", filterGroups);
  const sidebar = h("aside.card.filters", h("div.card-body",
    h("button.row.filter-toggle", { type: "button", onclick: () => groupsBox.classList.toggle("open") }, icon("filter"), h("strong", `Filtrar ${mod.plural.toLowerCase()}`)),
    h("div", { style: { marginTop: "10px" } }, searchInput), groupsBox));

  if (view === "kanban") {
    const board = h("div");
    page.append(header, board);
    const loadBoard = async () => {
      const params = { ...state.filters, search: state.search };
      countEl.textContent = await renderKanban(board, mod, params);
    };
    // En el tablero los filtros van arriba, compactos.
    const filtersRow = h("div.row", { style: { marginBottom: "12px", flexWrap: "wrap" } },
      h("div", { style: { width: "260px" } }, searchInput),
      h("select.select", { style: { width: "220px" }, onchange: (e) => { state.filters.assigned_to = e.target.value; loadBoard(); } },
        h("option", { value: "" }, "Todos los propietarios"), users.map((u) => h("option", { value: u.id }, u.full_name))));
    header.after(filtersRow);
    searchInput.addEventListener("input", debounce(() => { state.search = searchInput.value.trim(); loadBoard(); }, 300));
    return loadBoard();
  }

  // ---- Tabla ----
  searchInput.addEventListener("input", debounce(() => { state.search = searchInput.value.trim(); state.page = 1; load(); }, 300));
  const toolbar = h("div.toolbar");
  const tableWrap = h("div.table-wrap");
  const pager = h("div.pager");
  page.append(header, h("div.listview", sidebar, h("section.card", toolbar, tableWrap, pager)));

  async function load() {
    tableWrap.replaceChildren(spinner());
    const params = { page: state.page, page_size: state.pageSize, ordering: state.ordering, search: state.search, ...state.filters };
    const data = await api(`${mod.endpoint}/`, { params });
    countEl.textContent = data.count;
    state.rows = data.results;
    state.count = data.count;
    state.selected.clear();
    drawToolbar();
    if (!data.results.length) {
      tableWrap.replaceChildren(emptyState(state.search || Object.values(state.filters).some(Boolean) ? "No hay resultados con estos filtros." : `Todavía no hay ${mod.plural.toLowerCase()}. Creá ${mod.gender === "f" ? "la primera" : "el primero"}.`));
      pager.replaceChildren();
      return;
    }
    const allBox = h("input.checkbox", { type: "checkbox", "aria-label": "Seleccionar todo", onchange: (e) => {
      tbody.querySelectorAll("input.checkbox").forEach((c) => { c.checked = e.target.checked; c.dispatchEvent(new Event("change")); });
    } });
    const thead = h("thead", h("tr", h("th.no-sort", { style: { width: "36px" } }, allBox), mod.columns.map((c) => {
      const active = state.ordering.replace("-", "") === c.sort;
      return h(`th${c.sort ? "" : ".no-sort"}${active ? ".sorted" : ""}`, {
        class: ["money", "number", "percent"].includes(c.type) ? "num" : "",
        onclick: () => { if (!c.sort) return; state.ordering = state.ordering === c.sort ? `-${c.sort}` : c.sort; load(); },
      }, c.label, active ? (state.ordering.startsWith("-") ? " ↓" : " ↑") : "");
    })));
    const tbody = h("tbody");
    for (const r of data.results) {
      const box = h("input.checkbox", { type: "checkbox", onchange: (e) => {
        e.target.checked ? state.selected.add(r.id) : state.selected.delete(r.id);
        tr.classList.toggle("selected", e.target.checked); drawToolbar();
      } });
      const cells = await Promise.all(mod.columns.map(async (c) => {
        let content;
        if (c.link) content = h("a.cell-name", { href: `#/${mod.path}/${r.id}` }, c.name === "_title" ? recordTitle(mod, r) : r[c.name] || "(sin nombre)");
        else if (c.lookup && r[c.lookup.id]) content = h("a", { href: `#/${MODULES[c.lookup.module].path}/${r[c.lookup.id]}` }, r[c.name]);
        else content = await displayValue(c, r);
        return h("td", { class: ["money", "number", "percent"].includes(c.type) ? "num" : "" }, content);
      }));
      const tr = h("tr", h("td", box), cells);
      tbody.append(tr);
    }
    tableWrap.replaceChildren(h("table.grid", thead, tbody));

    const pages = Math.max(1, Math.ceil(data.count / state.pageSize));
    pager.replaceChildren(
      h("span", `Total: ${data.count} registros`), h("span.grow"),
      h("select.select.btn-sm", { style: { width: "auto", height: "30px" }, onchange: (e) => { state.pageSize = Number(e.target.value); state.page = 1; load(); } },
        PAGE_SIZES.map((n) => h("option", { value: n, selected: n === state.pageSize }, `${n} por página`))),
      h("button.btn.btn-sm", { disabled: !data.previous, onclick: () => { state.page--; load(); } }, "‹ Anterior"),
      h("span", `${state.page} de ${pages}`),
      h("button.btn.btn-sm", { disabled: !data.next, onclick: () => { state.page++; load(); } }, "Siguiente ›"),
    );
  }

  function drawToolbar() {
    const n = state.selected.size;
    toolbar.classList.toggle("selection-bar", n > 0);
    toolbar.replaceChildren(...(n
      ? [h("strong", `${n} seleccionado${n > 1 ? "s" : ""}`), h("span.grow"),
         ...massUpdateButtons(),
         h("button.btn.btn-sm", { onclick: () => exportCsv(mod, state.rows.filter((r) => state.selected.has(r.id)), meta, stages) }, icon("download"), "Exportar"),
         h("button.btn.btn-sm.btn-danger", { onclick: bulkDelete }, icon("trash"), "Eliminar")]
      : [h("span.muted", `Todos ${mod.gender === "f" ? "las" : "los"} ${mod.plural.toLowerCase()}`), h("span.grow"),
         h("button.btn.btn-sm.btn-ghost", { onclick: exportAll, title: "Exportar a CSV (Excel)" }, icon("download"), "Exportar"),
         h("button.btn.btn-sm.btn-ghost", { onclick: load, title: "Actualizar" }, icon("refresh"))]));
  }

  // Actualización masiva (como el "Mass Update" de Zoho): propietario, estado o etapa.
  function massUpdateButtons() {
    const ownerField = mod.sections.flatMap((s) => s.fields).find((f) => f.type === "user");
    const options = [];
    if (ownerField) options.push({ label: "Propietario", field: ownerField.name, choices: users.map((u) => ({ value: u.id, label: u.full_name })) });
    if (mod.endpoint === "leads") options.push({ label: "Estado", field: "status", choices: meta.lead_status.filter((c) => c.value !== "CONVERTIDO") });
    if (mod.endpoint === "opportunities") options.push({ label: "Etapa", field: "stage", choices: stages.filter((s) => s.is_active).map((s) => ({ value: s.id, label: s.name, probability: s.probability })) });
    return options.map((opt) => {
      const btn = h("button.btn.btn-sm", { onclick: () => popover(btn, [
        h("div.group-title", `Cambiar ${opt.label.toLowerCase()} a…`),
        ...opt.choices.map((c) => h("button.item", { onclick: () => massUpdate(opt, c) }, c.label)),
      ]) }, `Cambiar ${opt.label.toLowerCase()}`);
      return btn;
    });
  }

  async function massUpdate(opt, choice) {
    const body = { [opt.field]: choice.value };
    if (opt.field === "stage") body.probability = choice.probability;
    let failed = 0;
    for (const id of state.selected) {
      try { await api(`${mod.endpoint}/${id}/`, { method: "PATCH", body }); } catch { failed++; }
    }
    failed ? toast(`${failed} no se pudieron actualizar.`, "error") : toast(`${opt.label}: ${choice.label} (${state.selected.size} registros)`, "success");
    load();
  }

  async function exportAll() {
    const rows = [];
    const params = { page_size: 200, ordering: state.ordering, search: state.search, ...state.filters };
    for (let page = 1; page <= 25; page++) {
      const data = await api(`${mod.endpoint}/`, { params: { ...params, page } });
      rows.push(...data.results);
      if (!data.next) break;
    }
    exportCsv(mod, rows, meta, stages);
  }

  async function bulkDelete() {
    const n = state.selected.size;
    if (!(await confirmDialog(`Eliminar ${n} registro${n > 1 ? "s" : ""}`, "Esta acción no se puede deshacer."))) return;
    let failed = 0;
    for (const id of state.selected) {
      try { await api(`${mod.endpoint}/${id}/`, { method: "DELETE" }); } catch { failed++; }
    }
    failed ? toast(`${failed} no se pudieron eliminar (pueden tener registros asociados).`, "error") : toast("Registros eliminados", "success");
    load();
  }

  return load();
}

/** Descarga un CSV que Excel abre bien (separador ";" y acentos con BOM). */
function exportCsv(mod, rows, meta, stages) {
  if (!rows.length) return toast("No hay registros para exportar.", "error");
  const label = (key, v) => meta[key]?.find((c) => c.value === v)?.label || v || "";
  const value = (c, r) => {
    if (c.name === "_title") return recordTitle(mod, r);
    const v = r[c.name];
    if (c.type === "badge" || c.type === "choice") return label(c.choices, v);
    if (c.type === "stage") return r.stage_name || stages?.find((s) => s.id === r.stage)?.name || "";
    if (c.type === "money") return String(Number(v || 0)).replace(".", ",");
    if (c.type === "date") return v ? String(v).slice(0, 10) : "";
    return v ?? "";
  };
  const extra = ["email", "phone"].filter((k) => rows[0][k] !== undefined && !mod.columns.some((c) => c.name === k));
  const header = [...mod.columns.map((c) => c.label), ...extra.map((k) => (k === "email" ? "Correo" : "Teléfono"))];
  const lines = rows.map((r) => [...mod.columns.map((c) => value(c, r)), ...extra.map((k) => r[k] || "")]);
  const csv = [header, ...lines].map((line) => line.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(";")).join("\r\n");
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  const a = h("a", { href: URL.createObjectURL(blob), download: `${mod.plural.toLowerCase()}-${new Date().toISOString().slice(0, 10)}.csv` });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  toast(`${rows.length} registros exportados`, "success");
}
