/*
 * Cliente de la API de SOLVIS CRM, compartido por todos los fronts.
 *
 * Cada cliente (tenant) tiene su propio front en /frontends/<frontend>/,
 * pero todos hablan con el mismo back (/api/). Al iniciar sesión el back
 * devuelve user.tenant.frontend: si no es el front actual, se redirige.
 */
const API_BASE = "/api";
const STORE_KEY = "solvis_crm_session";

export class ApiError extends Error {
  constructor(status, data) {
    super(ApiError.message(data) || `Error ${status}`);
    this.status = status;
    this.data = data;
  }
  static message(data) {
    if (!data) return "";
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    const [field, msgs] = Object.entries(data)[0] || [];
    if (!field) return "";
    const msg = Array.isArray(msgs) ? msgs[0] : msgs;
    return field === "non_field_errors" ? msg : `${field}: ${msg}`;
  }
}

function readSession() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY)) || null; } catch { return null; }
}
function writeSession(s) {
  try { s ? localStorage.setItem(STORE_KEY, JSON.stringify(s)) : localStorage.removeItem(STORE_KEY); } catch {}
}

export const session = {
  get user() { return readSession()?.user || null; },
  get tenant() { return readSession()?.user?.tenant || null; },
  get isLoggedIn() { return !!readSession()?.access; },
};

let refreshing = null;
async function refreshAccess() {
  const s = readSession();
  if (!s?.refresh) throw new ApiError(401, { detail: "Sesión vencida" });
  refreshing ||= fetch(`${API_BASE}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: s.refresh }),
  }).then(async (r) => {
    if (!r.ok) throw new ApiError(401, { detail: "Sesión vencida" });
    const data = await r.json();
    writeSession({ ...readSession(), access: data.access, refresh: data.refresh || s.refresh });
  }).finally(() => { refreshing = null; });
  return refreshing;
}

export async function api(path, { method = "GET", body, params, retry = true } = {}) {
  let url = `${API_BASE}/${path.replace(/^\//, "")}`;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") qs.set(k, v); });
    if ([...qs].length) url += `?${qs}`;
  }
  const headers = { Accept: "application/json" };
  const s = readSession();
  if (s?.access) headers.Authorization = `Bearer ${s.access}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  if (res.status === 401 && retry && s?.refresh) {
    try { await refreshAccess(); } catch { logout(); throw new ApiError(401, { detail: "Sesión vencida" }); }
    return api(path, { method, body, params, retry: false });
  }
  if (res.status === 401 && s) { logout(); }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export async function login(username, password) {
  const data = await api("auth/login/", { method: "POST", body: { username, password }, retry: false });
  writeSession({ access: data.access, refresh: data.refresh, user: data.user });
  return data.user;
}

export async function refreshMe() {
  const user = await api("users/me/");
  writeSession({ ...readSession(), user });
  return user;
}

export function logout() {
  const s = readSession();
  writeSession(null);
  if (s?.refresh) {
    fetch(`${API_BASE}/auth/logout/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: s.refresh }),
    }).catch(() => {});
  }
}

/** Si el usuario pertenece a otro front, lo manda ahí. Devuelve true si redirigió. */
export function ensureFrontend(currentFrontend) {
  const target = session.tenant?.frontend;
  if (target && target !== currentFrontend) {
    location.replace(`/${target}/`);
    return true;
  }
  return false;
}
