import { describe, expect, it } from "vitest";

import { evenness, histogram, mean, slotSummaries } from "./stats";

describe("stats", () => {
  it("histogram is sorted numerically with shares", () => {
    expect(histogram({ "10": 1, "8": 3 })).toEqual([
      { label: "8", value: 3, share: 0.75 },
      { label: "10", value: 1, share: 0.25 },
    ]);
    expect(mean({ "8": 3, "10": 1 })).toBe(8.5);
  });

  it("evenness", () => {
    expect(evenness([5, 5, 5])).toBeCloseTo(1);
    expect(evenness([10, 0, 0])).toBe(0);
    expect(evenness([7])).toBe(1);
  });

  it("slot summaries list unused candidates", () => {
    const s = slotSummaries({
      variants: 4, distinct_combinations: 2, max_repeats: 2, family_skips: 0, total_complexity: {},
      slots: [{ title: "A", candidates: [{ ref: "x", complexity: 1, count: 4 }, { ref: "y", complexity: 2, count: 0 }] }],
    });
    expect(s[0].unused).toEqual(["y"]);
    expect(s[0].bars[0]).toMatchObject({ label: "x", share: 1 });
    expect(s[0].evenness).toBe(0);
  });
});
