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

// Menú lateral, agrupado como en Zoho CRM.
const NAV = [
  { items: [{ path: "home", label: "Inicio", icon: "home" }] },
  { title: "Ventas", items: [
    { path: "leads", label: "Leads", icon: "lead" },
    { path: "contacts", label: "Contactos", icon: "contact" },
    { path: "companies", label: "Empresas", icon: "company" },
    { path: "deals", label: "Oportunidades", icon: "deal" },
  ] },
  { title: "Actividades", items: [{ path: "tasks", label: "Tareas", icon: "task" }] },
];

// Menú de Configuración: reemplaza al menú principal mientras se está en #/settings.
const SETTINGS_NAV = [
  { title: "General", items: [{ path: "settings/company", label: "Información de la empresa", icon: "company" }] },
  { title: "Usuarios y permisos", items: [{ path: "settings/users", label: "Usuarios", icon: "users" }] },
  { title: "Personalización", items: [{ path: "settings/stages", label: "Pipeline de ventas", icon: "kanban" }] },
];
const SECTION_TITLES = { home: ["Inicio", "home"], tasks: ["Actividades", "task"], search: ["Búsqueda", "search"], settings: ["Configuración", "settings"] };

const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(`solvis_crm_${k}`)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(`solvis_crm_${k}`, JSON.stringify(v)); } catch {} },
};

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

// ---------- Menú lateral y cabecera ----------
let shell, crumb;
const isMobile = () => matchMedia("(max-width: 860px)").matches;
function applyCollapsed() { shell.classList.toggle("collapsed", !isMobile() && store.get("collapsed", false)); }

function sidebar() {
  const user = session.user;
  const tenant = session.tenant;
  // Filtra las opciones del menú, como el "Buscar" del menú de Zoho.
  const search = h("input", {
    type: "search", placeholder: "Buscar en el menú",
    oninput: () => {
      const q = search.value.trim().toLowerCase();
      document.querySelectorAll(".sidebar .sb-link").forEach((a) => a.classList.toggle("hidden", !!q && !a.textContent.toLowerCase().includes(q)));
      document.querySelectorAll(".sidebar .sb-group").forEach((g) => {
        if (q) g.classList.remove("closed");
        g.classList.toggle("hidden", !!q && !g.querySelector(".sb-link:not(.hidden)"));
      });
    },
  });
  const closedGroups = store.get("closed_groups", []);
  const link = (it) => h("a.sb-link", { href: `#/${it.path}`, dataset: { path: it.path }, title: it.label }, icon(it.icon), h("span.sb-label", it.label));
  const groups = NAV.map((g) => {
    if (!g.title) return g.items.map(link);
    const box = h(`div.sb-group${closedGroups.includes(g.title) ? ".closed" : ""}`,
      h("button.sb-group-title", { type: "button", onclick: () => {
        box.classList.toggle("closed");
        const closed = new Set(store.get("closed_groups", []));
        box.classList.contains("closed") ? closed.add(g.title) : closed.delete(g.title);
        store.set("closed_groups", [...closed]);
      } }, h("span", g.title), icon("chevron", "chev")),
      h("div.sb-items", g.items.map(link)));
    return box;
  });
  const settingsNav = h("div.sb-settings",
    h("a.sb-link.sb-back", { href: "#/home", onclick: (e) => { e.preventDefault(); location.hash = lastAppHash; } }, icon("back"), h("span.sb-label", "Volver al CRM")),
    h("a.sb-settings-title", { href: "#/settings", title: "Configuración" }, icon("settings"), h("span.sb-label", "Configuración")),
    SETTINGS_NAV.map((g) => h("div.sb-group", h("div.sb-group-title", h("span", g.title)), h("div.sb-items", g.items.map(link)))));
  return h("aside.sidebar",
    h("div.sb-top",
      h("a.brand", { href: "#/home" }, h("img", { src: tenant?.logo_url || "img/isotipo-blanco.png", alt: "" }), h("span", "Solvis CRM")),
      h("button.btn.btn-ghost.btn-icon.sb-collapse", { title: "Contraer menú", onclick: () => { store.set("collapsed", !store.get("collapsed", false)); applyCollapsed(); } }, icon("panel"))),
    h("div.sb-scroll.sb-settings-scroll", settingsNav),
    h("div.sb-scroll.sb-main-scroll",
      groups.slice(0, 1),
      h("div.sb-sep"),
      h("div.sb-tenant", { title: tenant?.name || "" }, avatar(tenant?.name || "S"), h("span.sb-label", tenant?.name || "")),
      h("div.sb-search", icon("search"), search),
      groups.slice(1)),
    h("div.sb-foot",
      avatar(user?.full_name || user?.username),
      h("div.who", h("div", { style: { color: "#fff", fontWeight: 600 } }, user?.full_name), h("div.small", user?.role || "")),
      h("button.btn.btn-ghost.btn-icon", { title: "Cerrar sesión", onclick: () => { logout(); renderLogin(); } }, icon("logout"))));
}

function header() {
  crumb = h("div.crumb");
  const search = h("input", {
    type: "search", placeholder: "Buscar registros",
    onkeydown: (e) => { if (e.key === "Enter" && search.value.trim()) location.hash = `#/search?q=${encodeURIComponent(search.value.trim())}`; },
  });
  const plusBtn = h("button.btn.btn-primary.btn-create", { title: "Crear", onclick: () => popover(plusBtn, [
    h("div.group-title", "Crear"),
    ...Object.values(MODULES).map((m) => h("a.item", { href: `#/${m.path}/new` }, icon(m.icon), `${m.gender === "f" ? "Nueva" : "Nuevo"} ${m.singular.toLowerCase()}`)),
    h("button.item", { onclick: () => openTaskModal({ onSaved: () => route() }) }, icon("task"), "Nueva tarea"),
  ], { align: "right" }) }, icon("plus"));
  const user = session.user;
  const av = avatar(user?.full_name || user?.username);
  av.title = user?.full_name || "";
  av.addEventListener("click", () => popover(av, [
    h("div.head", h("div", { style: { fontWeight: 600 } }, user?.full_name), h("div.muted.small", session.tenant?.name || ""), h("div.muted.small", user?.role || "")),
    h("div.sep"),
    h("a.item", { href: "#/settings" }, icon("settings"), "Configuración"),
    h("button.item", { onclick: () => { logout(); renderLogin(); } }, icon("logout"), "Cerrar sesión"),
  ], { align: "right" }));
  return h("header.topbar",
    h("button.btn.btn-ghost.btn-icon.menu-btn", { title: "Menú", onclick: () => shell.classList.add("mobile-open") }, icon("menu")),
    crumb,
    h("div.top-search", icon("search"), search),
    h("div.topbar-right",
      plusBtn,
      h("a.btn.btn-ghost.btn-icon", { href: "#/tasks", title: "Mis tareas" }, icon("task")),
      h("a.btn.btn-ghost.btn-icon.settings-btn", { href: "#/settings", title: "Configuración" }, icon("settings")),
      av));
}

let lastAppHash = "#/home";
function setActive(section, sub) {
  const inSettings = section === "settings";
  shell.classList.toggle("settings-mode", inSettings);
  if (!inSettings) lastAppHash = location.hash || "#/home";
  const key = inSettings ? (sub ? `settings/${sub}` : "") : section;
  document.querySelectorAll(".sb-link").forEach((a) => a.classList.toggle("active", a.dataset.path === key));
  const mod = byPath(section);
  const [label, ic] = mod ? [mod.plural, mod.icon] : SECTION_TITLES[section] || ["", "home"];
  crumb.replaceChildren(icon(ic), label);
  shell.classList.remove("mobile-open");
}

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
  setActive(section, id);
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
  shell = h("div.shell", sidebar(), h("div.sb-backdrop", { onclick: () => shell.classList.remove("mobile-open") }), h("div.main-area", header(), main));
  root.replaceChildren(shell);
  applyCollapsed();
  route();
}

window.addEventListener("resize", () => shell && applyCollapsed());
window.addEventListener("hashchange", () => main && session.isLoggedIn && route());
window.addEventListener("unhandledrejection", (e) => { if (e.reason instanceof ApiError) toast(e.reason.message, "error"); });
session.isLoggedIn ? start() : renderLogin();
