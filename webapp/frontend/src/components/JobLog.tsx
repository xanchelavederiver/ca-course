import { Alert, Badge, Code, Group, Loader, Progress, ScrollArea, Spoiler, Stack, Text } from "@mantine/core";
import { useEffect, useRef, type ReactNode } from "react";

import { useJob } from "../api/hooks";
import type { Job, JobStatus } from "../api/types";

const COLORS: Record<JobStatus, string> = { queued: "gray", running: "blue", done: "green", failed: "red" };

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <Badge color={COLORS[status]} variant="light" leftSection={status === "running" ? <Loader size={10} /> : null}>
      {status}
    </Badge>
  );
}

/** Live log of a job (SSE). `children` renders the result once the job is done. */
export function JobLog<R>({ jobId, children, onDone, compact }: {
  jobId: string | null;
  children?: (result: R, job: Job<R>) => ReactNode;
  onDone?: (job: Job<R>) => void;
  compact?: boolean;
}) {
  const { job, events } = useJob<R>(jobId);
  const doneRef = useRef<string | null>(null);
  useEffect(() => {
    if (job && (job.status === "done" || job.status === "failed") && doneRef.current !== job.id) {
      doneRef.current = job.id;
      onDone?.(job);
    }
  }, [job, onDone]);

  if (!jobId) return null;
  const logs = events.filter((e) => e.type === "log");
  const last = logs[logs.length - 1];
  const progress = last && typeof last.total === "number" ? ((last.done as number) / (last.total as number)) * 100 : null;

  return (
    <Stack gap="xs">
      <Group gap="xs">
        <Text size="sm" fw={500}>{job?.title ?? "job"}</Text>
        {job && <StatusBadge status={job.status} />}
      </Group>
      {progress !== null && job?.status === "running" && <Progress value={progress} size="sm" />}
      {logs.length > 0 && (
        <ScrollArea.Autosize mah={compact ? 120 : 220} type="auto">
          <Code block style={{ fontSize: 11 }}>
            {logs.map((e) => (
              <div key={e.seq} style={{ color: e.level === "warning" || e.ok === false ? "var(--mantine-color-red-7)" : undefined }}>
                {new Date(e.t * 1000).toLocaleTimeString()} {e.message}
              </div>
            ))}
          </Code>
        </ScrollArea.Autosize>
      )}
      {job?.status === "failed" && job.error && (
        <Alert color="red" title={job.error.message} variant="light">
          <Spoiler maxHeight={0} showLabel="traceback" hideLabel="hide">
            <Code block style={{ whiteSpace: "pre-wrap", fontSize: 11 }}>{job.error.traceback}</Code>
          </Spoiler>
        </Alert>
      )}
      {job?.status === "done" && job.result != null && children?.(job.result as R, job)}
    </Stack>
  );
}
