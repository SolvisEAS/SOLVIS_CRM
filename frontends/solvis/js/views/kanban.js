// Tablero de oportunidades por etapa, con arrastrar y soltar (vista Kanban de Zoho).
import { api } from "/shared/api.js";
import { getStages } from "../modules.js";
import { date, emptyState, h, shortMoney, toast } from "../ui.js";

export async function renderKanban(board, mod, params) {
  const [stages, data] = await Promise.all([
    getStages(),
    api(`${mod.endpoint}/`, { params: { ...params, page_size: 200, ordering: "expected_closing_date" } }),
  ]);
  const active = stages.filter((s) => s.is_active);
  if (!active.length) { board.replaceChildren(emptyState("No hay etapas configuradas.")); return 0; }
  const byStage = new Map(active.map((s) => [s.id, []]));
  data.results.forEach((o) => byStage.get(o.stage)?.push(o));

  const columns = active.map((stage) => {
    const items = byStage.get(stage.id);
    const total = items.reduce((a, o) => a + Number(o.amount), 0);
    const cards = h("div.kanban-cards", items.map((o) => card(o)));
    const col = h("div.kanban-col",
      h("div.kanban-head", { style: { borderTopColor: stage.color || "var(--accent)" } },
        h("div.name", stage.name, h("span.muted.small", `(${items.length})`)),
        h("div.sum", `${shortMoney(total)} · ${stage.probability}%`)),
      cards);
    col.addEventListener("dragover", (e) => { e.preventDefault(); col.classList.add("drag-over"); });
    col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
    col.addEventListener("drop", async (e) => {
      e.preventDefault(); col.classList.remove("drag-over");
      const id = Number(e.dataTransfer.getData("text/plain"));
      const opp = data.results.find((o) => o.id === id);
      if (!opp || opp.stage === stage.id) return;
      try {
        await api(`${mod.endpoint}/${id}/`, { method: "PATCH", body: { stage: stage.id, probability: stage.probability } });
        toast(`"${opp.name}" pasó a ${stage.name}`, "success");
        await renderKanban(board, mod, params);
      } catch (ex) { toast(ex.message, "error"); }
    });
    return col;
  });
  board.replaceChildren(h("div.kanban", columns));
  return data.count;

  function card(o) {
    const el = h("a.kcard", { href: `#/${mod.path}/${o.id}`, draggable: "true", style: { textDecoration: "none", color: "inherit", display: "block" } },
      h("div.t", o.name),
      h("div.muted.small", o.company_name),
      o.contact_name ? h("div.muted.small", o.contact_name) : null,
      h("div.row", { style: { marginTop: "6px" } },
        h("div.amt", shortMoney(o.amount)),
        o.expected_closing_date ? h("span.muted.small", { style: { marginLeft: "auto" } }, date(o.expected_closing_date)) : null));
    el.addEventListener("dragstart", (e) => { e.dataTransfer.setData("text/plain", o.id); el.classList.add("dragging"); });
    el.addEventListener("dragend", () => el.classList.remove("dragging"));
    return el;
  }
}
