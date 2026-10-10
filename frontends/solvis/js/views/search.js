// Búsqueda global en todos los módulos.
import { api } from "/shared/api.js";
import { icon } from "../icons.js";
import { MODULES, recordTitle } from "../modules.js";
import { emptyState, h } from "../ui.js";

export async function renderSearch(page, q) {
  document.title = `Buscar "${q}" · Solvis CRM`;
  const results = await Promise.all(Object.values(MODULES).map(async (mod) => ({ mod, data: await api(`${mod.endpoint}/`, { params: { search: q, page_size: 10 } }) })));
  const total = results.reduce((a, r) => a + r.data.count, 0);
  page.append(h("div.page-header", h("h1", `Resultados para "${q}"`), h("span.count", total)));
  if (!total) return page.append(h("div.card", emptyState("No encontramos nada con esa búsqueda.", "search")));
  for (const { mod, data } of results) {
    if (!data.count) continue;
    page.append(h("section.card", { style: { marginBottom: "14px" } },
      h("div.card-header", icon(mod.icon), h("h3", mod.plural), h("span.muted", `(${data.count})`),
        data.count > 10 ? h("a.small", { href: `#/${mod.path}?search=${encodeURIComponent(q)}`, style: { marginLeft: "auto" } }, "Ver todos") : null),
      h("ul.mini-list", data.results.map((r) => h("li",
        h("div.grow", h("a.title", { href: `#/${mod.path}/${r.id}` }, recordTitle(mod, r)), h("div.muted.small", mod.subtitle(r))))))));
  }
}
