import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { enc, get, patch, post, put } from "./client";
import type {
  EngineStatus, GitStatus, Job, JobEvent, PreviewResult, RunDetail, RunSummary, SheetDetail,
  SheetSummary, TaskDetail, TaskList, Topic, ValidationResult, VariantStats,
} from "./types";

export const keys = {
  tasks: ["tasks"] as const,
  task: (id: string) => ["task", id] as const,
  topics: ["topics"] as const,
  sheets: ["sheets"] as const,
  sheet: (path: string) => ["sheet", path] as const,
  archive: ["archive"] as const,
  run: (sheet: string, run: string) => ["run", sheet, run] as const,
  git: ["git"] as const,
  engine: ["engine"] as const,
  jobs: ["jobs"] as const,
  macros: ["macros"] as const,
};

export const useTasks = () => useQuery({ queryKey: keys.tasks, queryFn: () => get<TaskList>("/tasks") });
export const useTask = (id: string) =>
  useQuery({ queryKey: keys.task(id), queryFn: () => get<TaskDetail>(`/tasks/${encodeURIComponent(id)}`) });
export const useTopics = () => useQuery({ queryKey: keys.topics, queryFn: () => get<Topic[]>("/topics") });
export const useSheets = () => useQuery({ queryKey: keys.sheets, queryFn: () => get<SheetSummary[]>("/sheets") });
export const useSheet = (path: string) =>
  useQuery({ queryKey: keys.sheet(path), queryFn: () => get<SheetDetail>(`/sheets/${enc(path)}`) });
export const useArchive = () =>
  useQuery({ queryKey: keys.archive, queryFn: () => get<{ sheet_id: string; runs: RunSummary[] }[]>("/archive") });
export const useRun = (sheet: string, run: string) =>
  useQuery({ queryKey: keys.run(sheet, run), queryFn: () => get<RunDetail>(`/archive/${sheet}/${run}`) });
export const useGitStatus = () =>
  useQuery({ queryKey: keys.git, queryFn: () => get<GitStatus>("/git/status"), refetchInterval: 10_000 });
export const useEngine = () =>
  useQuery({ queryKey: keys.engine, queryFn: () => get<EngineStatus>("/engine"), refetchInterval: 4000 });
export const useJobs = () => useQuery({ queryKey: keys.jobs, queryFn: () => get<Job[]>("/jobs"), refetchInterval: 3000 });
export const useMacros = () =>
  useQuery({ queryKey: keys.macros, queryFn: () => get<Record<string, string | [string, number]>>("/latex/macros"), staleTime: Infinity });

export function usePreview(ref: string) {
  return useMutation({
    mutationFn: (body: { seed?: number | null; count?: number; statement?: string | null; solution?: string | null; pdf?: boolean }) =>
      post<PreviewResult>(`/tasks/${encodeURIComponent(ref)}/preview`, body),
  });
}

export function useValidateTask(ref: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (count: number) => post<ValidationResult>(`/tasks/${encodeURIComponent(ref)}/validate`, { count }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.tasks }),
  });
}

export function useSaveTaskMeta(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      patch<{ id: string; source: string }>(`/tasks/${encodeURIComponent(id)}/meta`, { values }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.tasks });
      qc.invalidateQueries({ queryKey: ["task"] });
      qc.invalidateQueries({ queryKey: keys.git });
    },
  });
}

export function useSaveTaskSource(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (source: string) =>
      put<{ ok: boolean; syntax_error: string | null }>(`/tasks/${encodeURIComponent(id)}/source`, { source }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.tasks });
      qc.invalidateQueries({ queryKey: keys.task(id) });
      qc.invalidateQueries({ queryKey: keys.git });
    },
  });
}

export function useSheetStats() {
  return useMutation({
    mutationFn: (body: { yaml: string; seed?: number; samples?: number | null }) => post<VariantStats>("/sheets/stats", body),
  });
}

/** Follows a job over SSE; returns the job state as events arrive. */
export function useJob<R = unknown>(jobId: string | null) {
  const [job, setJob] = useState<Job<R> | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const qc = useQueryClient();
  const qcRef = useRef(qc);
  qcRef.current = qc;

  useEffect(() => {
    setEvents([]);
    setJob(null);
    if (!jobId) return;
    let closed = false;
    get<Job<R>>(`/jobs/${jobId}`).then((j) => !closed && setJob(j)).catch(() => {});
    const es = new EventSource(`/api/jobs/${jobId}/events`);
    const onEvent = (msg: MessageEvent) => {
      const ev = JSON.parse(msg.data) as JobEvent;
      setEvents((prev) => (prev.some((e) => e.seq === ev.seq) ? prev : [...prev, ev]));
      if (ev.type === "status") {
        setJob((j) => (j ? { ...j, status: ev.status!, result: (ev.result as R) ?? j.result, error: ev.error ?? j.error } : j));
        if (ev.status === "done" || ev.status === "failed") {
          es.close();
          get<Job<R>>(`/jobs/${jobId}`).then((j) => !closed && setJob(j)).catch(() => {});
          for (const k of [keys.sheets, keys.archive, keys.git, keys.jobs, keys.tasks]) {
            qcRef.current.invalidateQueries({ queryKey: k });
          }
        }
      }
    };
    es.addEventListener("status", onEvent);
    es.addEventListener("log", onEvent);
    // stream lost (server restart, proxy): poll until the job has finished
    let timer: ReturnType<typeof setInterval> | undefined;
    es.onerror = () => {
      es.close();
      if (closed || timer) return;
      timer = setInterval(async () => {
        try {
          const j = await get<Job<R>>(`/jobs/${jobId}`);
          if (closed) return;
          setJob(j);
          setEvents(j.events ?? []);
          if (j.status === "done" || j.status === "failed") clearInterval(timer);
        } catch {
          clearInterval(timer);
        }
      }, 1000);
    };
    return () => {
      closed = true;
      es.close();
      if (timer) clearInterval(timer);
    };
  }, [jobId]);

  return { job, events };
}
