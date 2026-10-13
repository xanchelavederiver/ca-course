// Helpers for the variant statistics panel (see taskgen.service.variant_stats).

import type { VariantStats } from "../api/types";

export interface Bar {
  label: string;
  value: number;
  share: number; // 0..1 of the total
}

export function histogram(counts: Record<string, number>): Bar[] {
  const entries = Object.entries(counts).sort((a, b) => Number(a[0]) - Number(b[0]));
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;
  return entries.map(([label, value]) => ({ label, value, share: value / total }));
}

/** Normalized Shannon entropy (0 = always the same task, 1 = uniform over candidates). */
export function evenness(counts: number[]): number {
  const total = counts.reduce((s, c) => s + c, 0);
  const n = counts.length;
  if (!total || n < 2) return n < 2 ? 1 : 0;
  let h = 0;
  for (const c of counts) if (c > 0) h -= (c / total) * Math.log(c / total);
  return h / Math.log(n);
}

export interface SlotSummary {
  title: string;
  bars: (Bar & { complexity: number })[];
  unused: string[];
  evenness: number;
}

export function slotSummaries(stats: VariantStats): SlotSummary[] {
  return stats.slots.map((s) => {
    const total = s.candidates.reduce((n, c) => n + c.count, 0) || 1;
    const bars = s.candidates
      .map((c) => ({ label: c.ref, value: c.count, share: c.count / total, complexity: c.complexity }))
      .sort((a, b) => b.value - a.value || a.label.localeCompare(b.label));
    return {
      title: s.title,
      bars,
      unused: s.candidates.filter((c) => c.count === 0).map((c) => c.ref),
      evenness: evenness(s.candidates.map((c) => c.count)),
    };
  });
}

export function mean(counts: Record<string, number>): number {
  let n = 0;
  let s = 0;
  for (const [k, v] of Object.entries(counts)) {
    n += v;
    s += Number(k) * v;
  }
  return n ? s / n : 0;
}
