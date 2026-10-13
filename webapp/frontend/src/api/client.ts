// Thin fetch wrapper: JSON in/out, errors as ApiError with the backend's detail.

export class ApiError extends Error {
  status: number;
  detail: unknown;
  problems: string[];
  traceback: string | null;
  body: Record<string, unknown>;

  constructor(status: number, body: Record<string, unknown>) {
    const detail = body.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : detail && typeof detail === "object" && "problems" in detail
          ? "invalid input"
          : `HTTP ${status}`;
    super(msg);
    this.status = status;
    this.detail = detail;
    this.body = body;
    const nested = detail && typeof detail === "object" ? (detail as { problems?: string[] }).problems : undefined;
    this.problems = (body.problems as string[] | undefined) ?? nested ?? [];
    this.traceback = (body.traceback as string | undefined) ?? null;
  }
}

export async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  const ct = res.headers.get("content-type") ?? "";
  const data = ct.includes("application/json") && text ? JSON.parse(text) : text;
  if (!res.ok) {
    throw new ApiError(res.status, typeof data === "object" && data ? data : { detail: String(data) });
  }
  return data as T;
}

export const get = <T>(path: string) => api<T>("GET", path);
export const post = <T>(path: string, body: unknown = {}) => api<T>("POST", path, body);
export const put = <T>(path: string, body: unknown) => api<T>("PUT", path, body);
export const patch = <T>(path: string, body: unknown) => api<T>("PATCH", path, body);

/** URL of a repo file (build/, archive/, materials/) served by the API. */
export function fileUrl(path: string, opts: { download?: boolean; v?: string | number } = {}): string {
  const q = new URLSearchParams();
  if (opts.download) q.set("download", "1");
  if (opts.v !== undefined) q.set("v", String(opts.v));
  const qs = q.toString();
  return `/api/files/${path.split("/").map(encodeURIComponent).join("/")}${qs ? `?${qs}` : ""}`;
}

export function enc(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}
