export function ago(iso: string | number | null | undefined): string {
  if (iso == null) return "—";
  const t = typeof iso === "number" ? iso * 1000 : Date.parse(iso);
  if (Number.isNaN(t)) return String(iso);
  const s = Math.round((Date.now() - t) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return new Date(t).toLocaleString();
}

export function json(v: unknown): string {
  return JSON.stringify(v, null, 2);
}

export const shortSha = (s: string | null | undefined) => (s ? s.slice(0, 8) : "—");
