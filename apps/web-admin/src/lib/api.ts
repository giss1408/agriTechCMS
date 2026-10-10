// Thin client over the standard envelope {success, data, meta, errors}.
// Access token in memory + localStorage, refreshed transparently once on 401.

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

export type Meta = { page?: number; per_page?: number; total?: number } | null;
export type ApiErrorItem = { code: string; message: string; field?: string; [k: string]: unknown };

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public errors: ApiErrorItem[] = []) {
    super(message);
  }
}

type Tokens = { access_token: string; refresh_token: string };
const STORAGE_KEY = "cabosse.session";

function readTokens(): Tokens | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

let tokens: Tokens | null = readTokens();
const listeners = new Set<() => void>();

export function setTokens(next: Tokens | null) {
  tokens = next;
  try {
    if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* private mode: session lasts until reload */
  }
  listeners.forEach((l) => l());
}

export const isLoggedIn = () => tokens !== null;
export function onAuthChange(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

let refreshing: Promise<boolean> | null = null;
async function refresh(): Promise<boolean> {
  if (!tokens) return false;
  refreshing ??= fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  })
    .then(async (r) => {
      if (!r.ok) return false;
      const body = await r.json();
      setTokens({ access_token: body.data.access_token, refresh_token: body.data.refresh_token });
      return true;
    })
    .catch(() => false)
    .finally(() => (refreshing = null));
  return refreshing;
}

async function raw(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (tokens) headers.set("Authorization", `Bearer ${tokens.access_token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401 && retry && tokens && !path.startsWith("/auth/")) {
    if (await refresh()) return raw(path, init, false);
    setTokens(null);
  }
  return res;
}

// The last few failed calls, attached to problem reports so support can see what went wrong.
export const recentErrors: { at: string; path: string; status: number; code: string }[] = [];
function remember(path: string, status: number, code: string) {
  recentErrors.unshift({ at: new Date().toISOString(), path: path.split("?")[0], status, code });
  recentErrors.length = Math.min(recentErrors.length, 5);
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<{ data: T; meta: Meta }> {
  let res: Response;
  try {
    res = await raw(path, init);
  } catch {
    remember(path, 0, "network");
    throw new ApiError(0, "network", "Connexion impossible au serveur. Vérifiez votre connexion internet.");
  }
  let body: any = null;
  try {
    body = await res.json();
  } catch {
    throw new ApiError(res.status, "network", "Réponse illisible du serveur");
  }
  if (!res.ok || !body.success) {
    const first: ApiErrorItem = body?.errors?.[0] ?? { code: "error", message: res.statusText };
    remember(path, res.status, first.code);
    throw new ApiError(res.status, first.code, first.message, body?.errors ?? []);
  }
  return { data: body.data as T, meta: body.meta };
}

export const api = {
  get: <T>(path: string, params?: Record<string, unknown>) => request<T>(path + qs(params)).then((r) => r.data),
  page: <T>(path: string, params?: Record<string, unknown>) => request<T>(path + qs(params)),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }).then((r) => r.data),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body) }).then((r) => r.data),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body) }).then((r) => r.data),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }).then((r) => r.data),
};

export function qs(params?: Record<string, unknown>): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "" && v !== false) sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/** Authenticated file download (CSV, GeoJSON) — a plain <a href> cannot send the Bearer token. */
export async function download(path: string, fallbackName: string) {
  const res = await raw(path);
  if (!res.ok) throw new ApiError(res.status, "download_failed", "Téléchargement impossible");
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Authenticated image as an object URL (QR codes). */
export async function imageUrl(path: string): Promise<string> {
  const res = await raw(path);
  if (!res.ok) throw new ApiError(res.status, "image_failed", "Image indisponible");
  return URL.createObjectURL(await res.blob());
}
