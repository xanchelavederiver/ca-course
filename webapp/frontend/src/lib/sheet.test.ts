import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { dataToForm, formToData, parseStudents, parseYaml, refToString, variantCount } from "./sheet";

// vitest runs from webapp/frontend
const load = (p: string) => parseYaml(readFileSync(resolve(process.cwd(), "../..", p), "utf-8")).data;

describe("form <-> data", () => {
  for (const p of ["sheets/sem1/kontrolnaya.yaml", "sheets/sem2/kontrolnaya.yaml",
    "sheets/sem2/seminar-demo.yaml", "sheets/catalog/all-tasks.yaml"]) {
    it(`round-trips ${p} unchanged`, () => {
      const data = load(p);
      expect(formToData(dataToForm(data), data)).toEqual(data);
    });
  }

  it("does not add default keys", () => {
    const data = { id: "x", kind: "individual", title: "t", groups: [{ name: "a", count: 2 }], slots: [{ tasks: ["dlp.shanks"] }] };
    expect(formToData(dataToForm(data), data)).toEqual(data);
  });

  it("individual: budget, students, topics slots", () => {
    const data = load("sheets/sem2/kontrolnaya.yaml") as Record<string, unknown>;
    const f = dataToForm(data);
    expect(f.kind).toBe("individual");
    expect(f.budget).toEqual({ mode: "exact", value: 8 });
    expect(variantCount(f)).toBe(126);
    expect(f.slots[2]).toMatchObject({ source: "topics", topics: ["dlp"] });

    f.budget = { mode: "range", min: 6, max: null };
    f.groups[0] = { ...f.groups[0], mode: "students", students: ["Иванов", "Петров"] };
    f.slots[2] = { ...f.slots[2], source: "tasks", tasks: ["dlp.shanks"] };
    f.distinct_families = false;
    const out = formToData(f, data);
    expect(out.budget).toEqual({ min: 6, max: null });
    expect((out.groups as unknown[])[0]).toEqual({ name: "6411", students: ["Иванов", "Петров"] });
    expect((out.slots as Record<string, unknown>[])[2]).toEqual({ title: "Дискретное логарифмирование", tasks: ["dlp.shanks"] });
    expect(out.distinct_families).toBe(false);
    expect(Object.keys(out).slice(0, 3)).toEqual(["id", "kind", "title"]);
    expect(variantCount(dataToForm(out))).toBe(86);
  });

  it("classroom: object refs become strings", () => {
    const f = dataToForm({ kind: "classroom", sections: [{ title: "s", tasks: [{ id: "a.b", preset: "sem2" }, "c.d"] }] });
    expect(f.sections[0].tasks).toEqual(["a.b@sem2", "c.d"]);
    expect(refToString({ id: "a.b", preset: null })).toBe("a.b");
  });

  it("keeps unknown keys", () => {
    const data = { id: "x", kind: "classroom", title: "t", sections: [], future_key: [1, 2] };
    expect(formToData(dataToForm(data), data).future_key).toEqual([1, 2]);
  });
});

describe("parseStudents", () => {
  it("accepts numbered and tabular lists", () => {
    expect(parseStudents("1. Иванов И.И.\n2) Петров П.П.\n\n3\tСидоров\tС.С.\nКузнецов")).toEqual([
      "Иванов И.И.", "Петров П.П.", "Сидоров С.С.", "Кузнецов",
    ]);
  });
});

describe("parseYaml", () => {
  it("reports errors", () => {
    expect(parseYaml("a: [").error).toBeTruthy();
    expect(parseYaml("").data).toEqual({});
  });
});
