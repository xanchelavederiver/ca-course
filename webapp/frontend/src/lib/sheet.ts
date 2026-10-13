// Sheet spec form model <-> YAML data (see taskgen/core/sheet.py).
//
// The YAML text is the canonical state of the sheet editor. The form works on
// a normalized copy (`SheetForm`) and is turned back into plain data with
// `formToData`; the backend merges that data into the YAML text so comments
// survive (`POST /api/sheets/merge`).

import { parse } from "yaml";

export type Kind = "classroom" | "individual";

export interface DocumentForm {
  font_size?: string;
  toc?: boolean;
  solutions_suffix?: string;
}

export interface SectionForm {
  title: string;
  intro?: string | null;
  tasks: string[];
}

export interface GroupForm {
  name: string;
  mode: "count" | "students";
  count: number;
  students: string[];
}

export interface SlotForm {
  title?: string | null;
  source: "tasks" | "topics";
  tasks: string[];
  topics: string[];
  complexity: number[] | null;
}

export type BudgetForm =
  | { mode: "none" }
  | { mode: "exact"; value: number }
  | { mode: "range"; min: number | null; max: number | null };

export interface SheetForm {
  kind: Kind;
  id: string;
  title: string;
  semester: number | null;
  preset: string | null;
  intro: string;
  template: string | null;
  document: DocumentForm | null;
  sections: SectionForm[];
  groups: GroupForm[];
  slots: SlotForm[];
  budget: BudgetForm;
  distinct_families: boolean;
  /** keys we do not model, kept as-is */
  extra: Record<string, unknown>;
}

const KNOWN = new Set([
  "kind", "id", "title", "semester", "preset", "intro", "template", "document",
  "sections", "groups", "slots", "budget", "distinct_families",
]);

/** Task ref: string "id" / "id@preset" or {id, preset} -> string form. */
export function refToString(ref: unknown): string {
  if (typeof ref === "string") return ref;
  if (ref && typeof ref === "object" && "id" in ref) {
    const r = ref as { id: string; preset?: string | null };
    return r.preset ? `${r.id}@${r.preset}` : r.id;
  }
  return String(ref);
}

export function splitRef(ref: string): { id: string; preset: string | null } {
  const [id, preset] = ref.split("@", 2);
  return { id, preset: preset || null };
}

const asStr = (v: unknown, d = ""): string => (typeof v === "string" ? v : v == null ? d : String(v));
const asList = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);

export function budgetFromData(b: unknown): BudgetForm {
  if (b == null) return { mode: "none" };
  if (typeof b === "number") return { mode: "exact", value: b };
  if (typeof b === "object") {
    const { min = null, max = null } = b as { min?: number | null; max?: number | null };
    if (min != null && min === max) return { mode: "exact", value: min };
    return { mode: "range", min, max };
  }
  return { mode: "none" };
}

export function budgetToData(b: BudgetForm): unknown {
  if (b.mode === "none") return null;
  if (b.mode === "exact") return b.value;
  return { min: b.min, max: b.max };
}

export function dataToForm(data: unknown): SheetForm {
  const d = (data && typeof data === "object" ? data : {}) as Record<string, unknown>;
  const extra: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(d)) if (!KNOWN.has(k)) extra[k] = v;
  return {
    kind: d.kind === "individual" ? "individual" : "classroom",
    id: asStr(d.id),
    title: asStr(d.title),
    semester: typeof d.semester === "number" ? d.semester : null,
    preset: typeof d.preset === "string" ? d.preset : null,
    intro: asStr(d.intro),
    template: typeof d.template === "string" ? d.template : null,
    document: d.document && typeof d.document === "object" ? (d.document as DocumentForm) : null,
    sections: asList(d.sections).map((s) => {
      const sec = (s ?? {}) as Record<string, unknown>;
      return { title: asStr(sec.title), intro: (sec.intro as string | null | undefined) ?? null, tasks: asList(sec.tasks).map(refToString) };
    }),
    groups: asList(d.groups).map((g) => {
      const gr = (g ?? {}) as Record<string, unknown>;
      const students = asList(gr.students).map((s) => asStr(s));
      const isStudents = Array.isArray(gr.students);
      return {
        name: asStr(gr.name),
        mode: isStudents ? "students" : "count",
        count: typeof gr.count === "number" ? gr.count : students.length || 1,
        students,
      };
    }),
    slots: asList(d.slots).map((s) => {
      const sl = (s ?? {}) as Record<string, unknown>;
      return {
        title: (sl.title as string | null | undefined) ?? null,
        source: Array.isArray(sl.topics) ? "topics" : "tasks",
        tasks: asList(sl.tasks).map(refToString),
        topics: asList(sl.topics).map((t) => asStr(t)),
        complexity: Array.isArray(sl.complexity) ? (sl.complexity as number[]) : null,
      };
    }),
    budget: budgetFromData(d.budget),
    distinct_families: d.distinct_families === undefined ? true : Boolean(d.distinct_families),
    extra,
  };
}

/**
 * Plain data for the YAML merge. Keys that the original data did not have and
 * that still hold their default are omitted, so a form round trip does not add
 * noise (e.g. `distinct_families: true`) to hand-written YAML.
 */
export function formToData(f: SheetForm, original: unknown): Record<string, unknown> {
  const orig = (original && typeof original === "object" ? original : {}) as Record<string, unknown>;
  const had = (k: string) => Object.prototype.hasOwnProperty.call(orig, k);
  const out: Record<string, unknown> = {};
  const set = (k: string, v: unknown, isDefault: boolean) => {
    if (had(k) || !isDefault) out[k] = v;
  };
  // keep the original key order where possible
  set("id", f.id, false);
  set("kind", f.kind, false);
  set("title", f.title, false);
  set("semester", f.semester, f.semester == null);
  set("preset", f.preset, f.preset == null);
  set("template", f.template, f.template == null);
  set("document", f.document, f.document == null);
  set("intro", f.intro, f.intro === "");
  if (f.kind === "classroom") {
    out.sections = f.sections.map((s) => {
      const sec: Record<string, unknown> = { title: s.title };
      if (s.intro) sec.intro = s.intro;
      sec.tasks = s.tasks;
      return sec;
    });
  } else {
    out.groups = f.groups.map((g) =>
      g.mode === "students" ? { name: g.name, students: g.students } : { name: g.name, count: g.count },
    );
    set("budget", budgetToData(f.budget), f.budget.mode === "none");
    out.slots = f.slots.map((s) => {
      const sl: Record<string, unknown> = {};
      if (s.title) sl.title = s.title;
      if (s.source === "tasks") sl.tasks = s.tasks;
      else sl.topics = s.topics;
      if (s.complexity && s.complexity.length) sl.complexity = s.complexity;
      return sl;
    });
    set("distinct_families", f.distinct_families, f.distinct_families === true);
  }
  Object.assign(out, f.extra);
  // order like the original document, new keys at the end
  const ordered: Record<string, unknown> = {};
  for (const k of Object.keys(orig)) if (k in out) ordered[k] = out[k];
  for (const k of Object.keys(out)) if (!(k in ordered)) ordered[k] = out[k];
  return ordered;
}

/** Parse YAML text; returns data or an error message. */
export function parseYaml(text: string): { data: unknown; error: string | null } {
  try {
    return { data: parse(text) ?? {}, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

/**
 * A pasted student list -> names. Accepts one name per line, optionally
 * numbered ("1. Иванов И.И.", "1) ...", "1\tИванов") or a spreadsheet column;
 * blank lines are dropped.
 */
export function parseStudents(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((l) => l.replace(/^\s*\d+\s*[.)\t:-]?\s*/, "").replace(/\t+/g, " ").trim())
    .filter(Boolean);
}

export function variantCount(f: SheetForm): number {
  if (f.kind === "classroom") return 1;
  return f.groups.reduce((n, g) => n + (g.mode === "students" ? g.students.length : g.count), 0);
}

export function emptySlot(): SlotForm {
  return { title: null, source: "tasks", tasks: [], topics: [], complexity: null };
}

export function emptyGroup(n: number): GroupForm {
  return { name: `group-${n}`, mode: "count", count: 30, students: [] };
}

export function moveItem<T>(xs: T[], from: number, to: number): T[] {
  const out = xs.slice();
  const [x] = out.splice(from, 1);
  out.splice(to, 0, x);
  return out;
}
