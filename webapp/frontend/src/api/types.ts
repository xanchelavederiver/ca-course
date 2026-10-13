// Response types of the taskgen web API (webapp/backend/taskgen_web/routers).

export interface Validation {
  ok: boolean;
  at: number;
  count: number;
  results?: CheckResult[];
}

export interface CheckResult {
  ref: string;
  ok: boolean;
  error: string | null;
  traceback: string | null;
  seed: number | null;
}

export interface TaskSummary {
  id: string;
  title: string;
  topics: string[];
  complexity: number | null;
  family: string | null;
  family_name: string | null;
  solution_detail: string | null;
  presets: string[];
  notes: string;
  module: string;
  class_name: string;
  file: string | null;
  line_start: number | null;
  line_end: number | null;
  validation: Validation | null;
  broken: boolean;
}

export interface TaskList {
  tasks: TaskSummary[];
  import_errors: Record<string, string>;
  syntax_errors: Record<string, string>;
}

export interface MetaField {
  defined: boolean;
  editable: boolean;
  value: unknown;
  expr: string | null;
}

export type MetaFieldName =
  | "id" | "title_ru" | "topics" | "complexity" | "family" | "solution_detail"
  | "presets" | "notes" | "statement" | "solution";

export interface TaskMeta {
  class_name: string;
  line: number;
  bases: string[];
  fields: Record<MetaFieldName, MetaField>;
}

export interface TaskInfo extends TaskSummary {
  statement: string;
  solution: string;
  preset_values: Record<string, Record<string, unknown>>;
}

export interface TaskDetail {
  id: string;
  file: string;
  class_name: string;
  source: string;
  meta: TaskMeta | null;
  meta_error: string | null;
  info: TaskInfo | null;
  info_error: string | null;
  import_error: string | null;
  validation: Validation | null;
}

export interface Instance {
  task_id: string;
  preset: string;
  seed: number;
  params: Record<string, unknown>;
  statement: string;
  solution: string;
  answer: unknown;
  complexity: number;
  title_ru: string;
}

export interface PreviewResult {
  seed: number;
  instances: Instance[];
  pdf: string | null;
  log: string | null;
}

export interface ValidationResult {
  ok: boolean;
  results: CheckResult[];
  taxonomy: string[];
  import_errors: Record<string, string>;
}

export interface Topic {
  slug: string;
  title: string;
  depth: number;
  count: number;
}

export interface SheetSummary {
  path: string;
  dir: string;
  id: string | null;
  kind: "classroom" | "individual" | null;
  title: string | null;
  semester: number | null;
  error: string | null;
  variants: number;
  last_draft: string | null;
  last_issue: { run: string; created_at: string | null } | null;
  issued_runs: number;
}

export interface VariantRef {
  key: string;
  group: string | null;
  number: number;
  student: string | null;
}

export interface DraftInfo {
  out_dir: string;
  created_at: string | null;
  master_seed: number | null;
  files: string[];
  pdfs: string[];
  variants: VariantRef[];
}

export interface SheetDetail {
  path: string;
  raw: string;
  data: unknown;
  problems: string[];
  draft: DraftInfo | null;
  runs: { run: string; created_at: string | null }[];
}

export interface GenResult {
  sheet_id: string;
  kind: "classroom" | "individual";
  master_seed: number;
  out_dir: string;
  manifest: string;
  files: string[];
  draft: boolean;
  git: { commit: string | null; dirty: boolean | null } | null;
  variants: (VariantRef & { tasks: string[] })[];
  pdfs: string[];
  warning?: string | null;
  sealed?: string[];
  dirty_files?: string[];
}

export interface RegenResult {
  identical: boolean;
  mismatches: string[];
  warnings: string[];
  checked: string[];
  out_dir: string;
  files: string[];
}

export interface JobEvent {
  seq: number;
  t: number;
  type: "status" | "log";
  status?: JobStatus;
  message?: string;
  result?: unknown;
  error?: JobError | null;
  [k: string]: unknown;
}

export type JobStatus = "queued" | "running" | "done" | "failed";

export interface JobError {
  kind: string;
  message: string;
  traceback: string;
}

export interface Job<R = unknown> {
  id: string;
  kind: string;
  title: string;
  status: JobStatus;
  created: number;
  finished: number | null;
  result: R | null;
  error: JobError | null;
  events?: JobEvent[];
}

export interface VariantStats {
  variants: number;
  distinct_combinations: number;
  max_repeats: number;
  family_skips: number;
  total_complexity: Record<string, number>;
  slots: { title: string; candidates: { ref: string; complexity: number; count: number }[] }[];
}

export interface RunSummary {
  run: string;
  sheet_id: string;
  created_at: string | null;
  master_seed: number;
  engine_version: string;
  git: { commit: string | null; dirty: boolean | null };
  layout: string;
  variants: number;
  sealed: string[];
  path: string;
  error?: string;
}

export interface ManifestVariant {
  key: string;
  group: string | null;
  number: number;
  student: string | null;
  digest: string;
  tasks: { slot: number; task: string; preset: string; complexity: number; seed: number; answer: unknown }[];
}

export interface RunDetail extends RunSummary {
  manifest: {
    spec_path: string | null;
    spec_source: string;
    files: Record<string, string>;
    variants: ManifestVariant[];
    [k: string]: unknown;
  };
  files_on_disk: string[];
}

export interface GitStatus {
  available: boolean;
  error?: string;
  branch?: string;
  head?: string;
  subject?: string;
  files: { path: string; status: string }[];
  dirty: boolean | null;
  dirty_files?: string[];
}

export interface EngineStatus {
  state: "stopped" | "starting" | "ready" | "busy" | "stale";
  restarts: number;
  started_at: number | null;
  pid: number | null;
  version?: string;
  tasks?: number;
  import_errors?: Record<string, string>;
  error?: string;
  latex: { configured: boolean; reachable: boolean };
  repo: string;
}
