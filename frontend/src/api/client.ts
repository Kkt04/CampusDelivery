/**
 * Thin fetch wrapper: adds the bearer token, parses JSON, and turns the
 * backend's `{error: {code, message, details}}` shape into an ApiError.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const TOKEN_KEY = "cdms.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }

  /** Field-level messages from a 422 response, keyed by field name. */
  get fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.details)) return {};
    return Object.fromEntries(
      (this.details as { field: string; message: string }[]).map((d) => [d.field, d.message.replace(/^Value error, /, "")]),
    );
  }
}

// sessionStorage: survives a page refresh, cleared when the tab closes (see docs/security notes).
export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

type Query = Record<string, string | number | boolean | null | undefined | string[]>;

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === false) return;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
    else params.append(key, String(value));
  });
  const qs = params.toString();
  return `${BASE_URL}${path}${qs ? `?${qs}` : ""}`;
}

export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  query?: Query;
  idempotencyKey?: string;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Cannot reach the server. Check your connection and try again.");
  }

  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const err = payload?.error;
    if (response.status === 401 && token) {
      tokenStore.clear();
      window.dispatchEvent(new Event("cdms:unauthorized"));
    }
    throw new ApiError(response.status, err?.code ?? "HTTP_ERROR", err?.message ?? `Request failed (${response.status})`, err?.details);
  }
  return payload as T;
}
