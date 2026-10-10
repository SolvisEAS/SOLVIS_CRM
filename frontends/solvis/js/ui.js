// Utilidades de interfaz: creación de elementos, formatos, modales y avisos.
import { icon } from "./icons.js";
import { session } from "/shared/api.js";

/** h("div.card#id", {attrs}, ...hijos) — arma elementos sin innerHTML (sin riesgo de XSS). */
export function h(spec, attrs, ...children) {
  if (attrs === null || typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs)) {
    children.unshift(attrs);
    attrs = {};
  }
  const [, tag = "div", rest = ""] = spec.match(/^([a-z0-9-]*)(.*)$/i);
  const el = document.createElement(tag || "div");
  rest.replace(/([.#])([\w-]+)/g, (_, t, v) => (t === "." ? el.classList.add(v) : (el.id = v)));
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "class") String(v).split(" ").filter(Boolean).forEach((c) => el.classList.add(c));
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k in el && typeof v !== "string") el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  append(el, children);
  return el;
}
function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}
export const clear = (el) => { el.replaceChildren(); return el; };

// ---------- Formatos ----------
export function money(v) {
  const currency = session.tenant?.currency || "PYG";
  const n = Number(v || 0);
  try {
    return new Intl.NumberFormat("es-PY", { style: "currency", currency, maximumFractionDigits: currency === "PYG" ? 0 : 2 }).format(n);
  } catch { return n.toLocaleString("es-PY"); }
}
export function shortMoney(v) {
  const n = Number(v || 0);
  const cur = session.tenant?.currency === "PYG" ? "Gs." : (session.tenant?.currency || "");
  if (n >= 1e9) return `${cur} ${(n / 1e9).toFixed(1).replace(".", ",")} mil M`;
  if (n >= 1e6) return `${cur} ${(n / 1e6).toFixed(1).replace(".", ",")} M`;
  return money(n);
}
export function date(v) {
  if (!v) return "";
  const d = new Date(v.length === 10 ? `${v}T12:00:00` : v);
  return d.toLocaleDateString("es-PY", { day: "2-digit", month: "short", year: "numeric" });
}
export function datetime(v) {
  if (!v) return "";
  return new Date(v).toLocaleString("es-PY", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
export function relDays(v) {
  if (!v) return "";
  const d = new Date(`${v}T00:00:00`), t = new Date(); t.setHours(0, 0, 0, 0);
  const diff = Math.round((d - t) / 86400000);
  if (diff === 0) return "Hoy";
  if (diff === 1) return "Mañana";
  if (diff === -1) return "Ayer";
  return diff < 0 ? `Hace ${-diff} días` : `En ${diff} días`;
}
export function initials(name) {
  return String(name || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";
}
const AVATAR_COLORS = ["#7B3FE4", "#0E7490", "#16367a", "#B45309", "#15803D", "#BE185D", "#4338CA", "#0369A1"];
export function avatar(name, cls = "") {
  const n = String(name || "");
  const color = AVATAR_COLORS[[...n].reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_COLORS.length];
  return h(`span.avatar${cls ? "." + cls : ""}`, { style: { background: color } }, initials(n));
}
export function badge(value, label, color) {
  const el = h(`span.badge.${value || "none"}`, label || value || "—");
  if (color) {
    el.style.background = `color-mix(in srgb, ${color} 14%, white)`;
    el.style.color = color;
    el.style.borderColor = "transparent";
    el.prepend(h("span.dot"));
  }
  return el;
}

// ---------- Avisos ----------
let toastBox;
export function toast(message, type = "") {
  toastBox ||= document.body.appendChild(h("div.toasts"));
  const el = h(`div.toast${type ? "." + type : ""}`, icon(type === "error" ? "close" : "check"), h("span", message));
  toastBox.append(el);
  setTimeout(() => el.remove(), type === "error" ? 6000 : 3200);
}

// ---------- Modales ----------
export function modal({ title, body, footer, width }) {
  const close = () => { backdrop.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = (e) => e.key === "Escape" && close();
  const box = h("div.modal", { style: width ? { maxWidth: width } : {} },
    h("div.modal-header", h("h3", title), h("button.btn.btn-ghost.btn-icon", { style: { marginLeft: "auto" }, onclick: close, "aria-label": "Cerrar" }, icon("close"))),
    h("div.modal-body", body),
    footer ? h("div.modal-footer", footer) : null,
  );
  const backdrop = h("div.modal-backdrop", { onmousedown: (e) => e.target === backdrop && close() }, box);
  document.body.append(backdrop);
  document.addEventListener("keydown", onKey);
  setTimeout(() => box.querySelector("input, select, textarea, button.btn-primary")?.focus(), 30);
  return { close, el: box };
}
export function confirmDialog(title, message, { okLabel = "Eliminar", danger = true } = {}) {
  return new Promise((resolve) => {
    let m;
    const done = (v) => { m.close(); resolve(v); };
    m = modal({
      title,
      body: h("p", { style: { margin: 0 } }, message),
      footer: [
        h("button.btn", { onclick: () => done(false) }, "Cancelar"),
        h(`button.btn.${danger ? "btn-danger" : "btn-primary"}`, { onclick: () => done(true) }, okLabel),
      ],
    });
  });
}

// ---------- Menú desplegable anclado a un botón ----------
export function popover(anchor, content, { align = "left" } = {}) {
  document.querySelectorAll(".dropdown.popover").forEach((d) => d.remove());
  const r = anchor.getBoundingClientRect();
  const dd = h("div.dropdown.popover", content);
  dd.style.top = `${r.bottom + window.scrollY + 6}px`;
  document.body.append(dd);
  const left = align === "right" ? r.right - dd.offsetWidth : r.left;
  dd.style.left = `${Math.max(8, left + window.scrollX)}px`;
  const off = (e) => { if (!dd.contains(e.target) && !anchor.contains(e.target)) { dd.remove(); document.removeEventListener("mousedown", off); } };
  setTimeout(() => document.addEventListener("mousedown", off), 0);
  dd.addEventListener("click", (e) => { if (e.target.closest(".item")) dd.remove(); });
  return dd;
}

export const spinner = () => h("div.spinner");
export function emptyState(text, iconName = "inbox") {
  return h("div.empty", icon(iconName), h("div", text));
}
export function debounce(fn, ms = 300) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
