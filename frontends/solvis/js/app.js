// Arranque del front general de Solvis: login, barra superior y rutas.
import { ApiError, ensureFrontend, login, logout, refreshMe, session } from "/shared/api.js";
import { icon } from "./icons.js";
import { MODULES, byPath, resetCaches } from "./modules.js";
import { avatar, h, popover, toast } from "./ui.js";
import { renderHome } from "./views/home.js";
import { renderList } from "./views/list.js";
import { renderDetail } from "./views/detail.js";
import { renderForm } from "./views/form.js";
import { renderTasks, openTaskModal } from "./views/tasks.js";
import { renderSearch } from "./views/search.js";
import { renderSettings } from "./views/settings.js";

const FRONTEND = "solvis";
const root = document.getElementById("app");

const TABS = [
  { path: "home", label: "Inicio", icon: "home" },
  { path: "leads", label: "Leads", icon: "lead" },
  { path: "contacts", label: "Contactos", icon: "contact" },
  { path: "companies", label: "Empresas", icon: "company" },
  { path: "deals", label: "Oportunidades", icon: "deal" },
  { path: "tasks", label: "Actividades", icon: "task" },
];

// ---------- Login ----------
function renderLogin(message) {
  document.title = "Iniciar sesión · Solvis CRM";
  const err = h("div.alert", { class: message ? "" : "hidden" }, message || "");
  const user = h("input.input#username", { autocomplete: "username", required: true, autofocus: true });
  const pass = h("input.input#password", { type: "password", autocomplete: "current-password", required: true });
  const btn = h("button.btn.btn-primary", { type: "submit" }, "Ingresar");
  const form = h("form", {
    onsubmit: async (e) => {
      e.preventDefault();
      btn.disabled = true; btn.textContent = "Ingresando…"; err.classList.add("hidden");
      try {
        await login(user.value.trim(), pass.value);
        if (!ensureFrontend(FRONTEND)) start();
      } catch (ex) {
        err.textContent = ex instanceof ApiError && ex.status === 401
          ? (ex.data?.code === "inactive_tenant" ? ex.message : "Usuario o contraseña incorrectos.")
          : "No se pudo conectar con el servidor. Probá de nuevo.";
        err.classList.remove("hidden");
        btn.disabled = false; btn.textContent = "Ingresar";
      }
    },
  },
    h("img", { src: "img/isotipo-violeta.png", alt: "", style: { height: "48px", alignSelf: "flex-start" } }),
    h("div", h("h1", "Bienvenido"), h("p.muted", { style: { margin: "4px 0 0" } }, "Ingresá con tu usuario de Solvis CRM.")),
    err,
    h("div.stack", { style: { gap: "6px" } }, h("label", { for: "username" }, "Usuario"), user),
    h("div.stack", { style: { gap: "6px" } }, h("label", { for: "password" }, "Contraseña"), pass),
    btn,
  );
  root.replaceChildren(h("div.login",
    h("div.login-brand",
      h("img", { src: "img/logo-blanco.png", alt: "Solvis" }),
      h("div", h("h2", "Tus clientes, tus ventas y tu equipo en un solo lugar."),
        h("p", "Leads, empresas, contactos y oportunidades con la forma de trabajar de Solvis.")),
      h("p.small", `© ${new Date().getFullYear()} Solvis EAS`),
    ),
    h("div.login-form", form),
  ));
}

// ---------- Barra superior ----------
function topbar() {
  const user = session.user;
  const search = h("input", {
    type: "search", placeholder: "Buscar en el CRM…",
    onkeydown: (e) => { if (e.key === "Enter" && search.value.trim()) location.hash = `#/search?q=${encodeURIComponent(search.value.trim())}`; },
  });
  const plusBtn = h("button.btn.btn-ghost.btn-icon", { title: "Crear", onclick: () => popover(plusBtn, [
    h("div.group-title", "Crear"),
    ...Object.values(MODULES).map((m) => h("a.item", { href: `#/${m.path}/new` }, icon(m.icon), `${m.gender === "f" ? "Nueva" : "Nuevo"} ${m.singular.toLowerCase()}`)),
    h("button.item", { onclick: () => openTaskModal({ onSaved: () => route() }) }, icon("task"), "Nueva tarea"),
  ], { align: "right" }) }, icon("plus"));
  const av = avatar(user?.full_name || user?.username);
  av.title = user?.full_name || "";
  av.addEventListener("click", () => popover(av, [
    h("div.head", h("div", { style: { fontWeight: 600 } }, user?.full_name), h("div.muted.small", user?.tenant?.name || ""), h("div.muted.small", user?.role || "")),
    h("div.sep"),
    h("a.item", { href: "#/settings" }, icon("settings"), "Configuración"),
    h("button.item", { onclick: () => { logout(); renderLogin(); } }, icon("logout"), "Cerrar sesión"),
  ], { align: "right" }));

  return h("header.topbar",
    h("a.brand", { href: "#/home" }, h("img", { src: tenantLogo(), alt: "" }), h("span", "CRM ", h("small", session.tenant?.slug === "solvis" ? "" : `· ${session.tenant?.name || ""}`))),
    h("nav.tabs", TABS.map((t) => h("a.tab", { href: `#/${t.path}`, dataset: { path: t.path } }, icon(t.icon), t.label))),
    h("div.topbar-right",
      h("div.global-search", icon("search"), search),
      plusBtn,
      h("a.btn.btn-ghost.btn-icon", { href: "#/settings", title: "Configuración" }, icon("settings")),
      av,
    ),
  );
}
const tenantLogo = () => session.tenant?.logo_url || "img/isotipo-blanco.png";

function applyBranding() {
  const t = session.tenant;
  if (t?.primary_color) document.documentElement.style.setProperty("--primary", t.primary_color);
  if (t?.accent_color) document.documentElement.style.setProperty("--accent", t.accent_color);
}

// ---------- Rutas ----------
let main;
function parseHash() {
  const [path, query = ""] = location.hash.replace(/^#\/?/, "").split("?");
  return { parts: path.split("/").filter(Boolean), query: new URLSearchParams(query) };
}

async function route() {
  if (!session.isLoggedIn) return renderLogin();
  const { parts, query } = parseHash();
  const [section = "home", id, action] = parts;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.path === section || (section === "search" && false)));
  window.scrollTo(0, 0);
  const page = h("main.page");
  main.replaceWith(page);
  main = page;
  try {
    const mod = byPath(section);
    if (section === "home") await renderHome(page);
    else if (section === "tasks") await renderTasks(page, query);
    else if (section === "search") await renderSearch(page, query.get("q") || "");
    else if (section === "settings") await renderSettings(page, id);
    else if (mod && !id) await renderList(page, mod, query);
    else if (mod && id === "new") await renderForm(page, mod, null, query);
    else if (mod && action === "edit") await renderForm(page, mod, id, query);
    else if (mod) await renderDetail(page, mod, id);
    else location.hash = "#/home";
  } catch (ex) {
    if (ex instanceof ApiError && ex.status === 401) return renderLogin("Tu sesión venció. Ingresá de nuevo.");
    console.error(ex);
    page.replaceChildren(h("div.card.empty", icon("close"), h("div", ex.status === 404 ? "No encontramos ese registro." : `Algo salió mal: ${ex.message}`)));
  }
}

async function start() {
  try { await refreshMe(); } catch (ex) { if (ex instanceof ApiError && ex.status === 401) return renderLogin(); }
  if (ensureFrontend(FRONTEND)) return;
  resetCaches();
  applyBranding();
  main = h("main.page");
  root.replaceChildren(topbar(), main);
  route();
}

window.addEventListener("hashchange", () => main && session.isLoggedIn && route());
window.addEventListener("unhandledrejection", (e) => { if (e.reason instanceof ApiError) toast(e.reason.message, "error"); });
session.isLoggedIn ? start() : renderLogin();
