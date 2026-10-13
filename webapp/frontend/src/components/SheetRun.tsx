import {
  Alert, Anchor, Button, Code, Group, List, Modal, NumberInput, SegmentedControl, SimpleGrid, Stack, Table, Text,
} from "@mantine/core";
import { IconCheck } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { fileUrl, post } from "../api/client";
import { useGitStatus, useSheetStats } from "../api/hooks";
import type { GenResult, VariantRef } from "../api/types";
import { histogram, mean, slotSummaries } from "../lib/stats";
import { ErrorAlert } from "./ErrorAlert";
import { JobLog } from "./JobLog";
import { PdfViewer } from "./PdfViewer";

export interface RunFiles {
  out_dir: string;
  files: string[];
  variants: VariantRef[];
  master_seed: number | null;
}

/** Per-group (sheet, solutions) pairs of a run, in group order. */
export function filePairs(run: RunFiles): { group: string | null; sheet: string; solutions: string }[] {
  const pdf = (f: string) => f.replace(/\.tex$/, ".pdf");
  const tex = run.files.filter((f) => f.endsWith(".tex"));
  const sheets = tex.filter((f) => !f.startsWith("tasks_solutions"));
  const sols = tex.filter((f) => f.startsWith("tasks_solutions"));
  const groups = [...new Set(run.variants.map((v) => v.group))];
  return sheets.map((s, i) => ({ group: sheets.length === groups.length ? groups[i] : null, sheet: pdf(s), solutions: pdf(sols[i] ?? s) }));
}

export function DraftView({ run, version }: { run: RunFiles; version: string | number }) {
  const pairs = filePairs(run);
  const [sel, setSel] = useState(0);
  const pair = pairs[Math.min(sel, pairs.length - 1)];
  if (!pair) return null;
  const nVariants = (g: string | null) => run.variants.filter((v) => v.group === g).length;
  return (
    <Stack gap="xs">
      <Group gap="xs">
        {pairs.length > 1 && (
          <SegmentedControl size="xs" value={String(sel)} onChange={(v) => setSel(Number(v))}
            data={pairs.map((p, i) => ({ value: String(i), label: `${p.group ?? i + 1} (${nVariants(p.group)})` }))} />
        )}
        <Text size="xs" c="dimmed">master seed {run.master_seed} · {run.out_dir}</Text>
      </Group>
      <SimpleGrid cols={2} spacing="xs">
        <PdfViewer key={`s${sel}`} path={`${run.out_dir}/${pair.sheet}`} version={version} height="72vh" />
        <PdfViewer key={`a${sel}`} path={`${run.out_dir}/${pair.solutions}`} version={version} height="72vh" />
      </SimpleGrid>
    </Stack>
  );
}

export function IssueDialog({ opened, onClose, path, variants, unsaved, problems }: {
  opened: boolean; onClose: () => void; path: string; variants: number; unsaved: boolean; problems: string[];
}) {
  const { data: git } = useGitStatus();
  const [seedMode, setSeedMode] = useState<"random" | "fixed">("random");
  const [seed, setSeed] = useState<number>(1);
  const [jobId, setJobId] = useState<string | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const dirty = !!git?.dirty;

  const issue = async () => {
    setErr(null);
    try {
      const r = await post<{ job: string }>("/runs/issue", { path, seed: seedMode === "fixed" ? seed : null });
      setJobId(r.job);
    } catch (e) {
      setErr(e);
    }
  };
  const close = () => {
    setJobId(null);
    setErr(null);
    onClose();
  };

  return (
    <Modal opened={opened} onClose={close} title={`Issue ${path}`} size="lg">
      <Stack gap="sm">
        <Text size="sm">Same path as <Code>make issue</Code>: generate → build every PDF → seal, into <Code>archive/&lt;id&gt;/&lt;timestamp&gt;/</Code>.
          Commit the run afterwards.</Text>
        <Group gap="md" align="flex-end">
          <SegmentedControl value={seedMode} onChange={(v) => setSeedMode(v as "random" | "fixed")}
            data={[{ value: "random", label: "random seed" }, { value: "fixed", label: "fixed seed" }]} disabled={!!jobId} />
          {seedMode === "fixed" && <NumberInput label="master seed" value={seed} onChange={(v) => setSeed(Number(v) || 0)} min={0} w={180} disabled={!!jobId} />}
          <Text size="sm">{variants} variant(s)</Text>
        </Group>
        {unsaved && <Alert color="orange">Save the sheet first: issuing uses the file on disk.</Alert>}
        {problems.length > 0 && <Alert color="red" title="The sheet is invalid">{problems.join("; ")}</Alert>}
        {git && !git.available && <Alert color="gray">No git repository: the manifest will not record a commit.</Alert>}
        {dirty ? (
          <Alert color="yellow" title="The working tree has uncommitted changes">
            <Text size="sm">You can issue anyway: the manifest records <Code>git.dirty: true</Code>, so its commit
              does not fully describe the generator. Committing first keeps the run exactly reproducible from git.</Text>
            <List size="xs" mt={4} mah={150} style={{ overflow: "auto" }}>
              {git?.dirty_files?.map((f) => <List.Item key={f}><Code>{f}</Code></List.Item>)}
            </List>
          </Alert>
        ) : git?.available && <Alert color="green" icon={<IconCheck />} p="xs">Working tree clean at {git.head?.slice(0, 8)}.</Alert>}
        <ErrorAlert error={err} />
        {!jobId && (
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button color="red" onClick={issue} disabled={unsaved || problems.length > 0}>Issue</Button>
          </Group>
        )}
        <JobLog<GenResult> jobId={jobId}>
          {(r) => (
            <Alert color="green" title={`Issued ${r.out_dir}`}>
              <Stack gap={4}>
                <Text size="sm">master seed {r.master_seed}, {r.variants.length} variant(s), sealed: {r.sealed?.join(", ")}</Text>
                <Group gap="xs">
                  {r.pdfs.map((p) => <Anchor key={p} href={fileUrl(p)} target="_blank" size="sm">{p.split("/").pop()}</Anchor>)}
                  <Anchor href={fileUrl(r.manifest)} target="_blank" size="sm">manifest.json</Anchor>
                </Group>
                <Anchor component={Link} to={`/archive/${r.sheet_id}/${r.out_dir.split("/").pop()}`} size="sm">Open in the archive →</Anchor>
                <Text size="xs" c="dimmed">Commit it: git add {r.out_dir}</Text>
                {r.dirty_files && r.dirty_files.length > 0 && (
                  <Text size="xs" c="orange">Issued from a dirty tree ({r.dirty_files.length} uncommitted file(s)); recorded as git.dirty.</Text>
                )}
              </Stack>
            </Alert>
          )}
        </JobLog>
      </Stack>
    </Modal>
  );
}

function Bars({ bars, color = "indigo" }: { bars: { label: string; value: number; share: number }[]; color?: string }) {
  const max = Math.max(...bars.map((b) => b.share), 0.0001);
  return (
    <Table fz="xs" verticalSpacing={1} withRowBorders={false}>
      <Table.Tbody>
        {bars.map((b) => (
          <Table.Tr key={b.label}>
            <Table.Td w={1} style={{ whiteSpace: "nowrap" }} ff="monospace">{b.label}</Table.Td>
            <Table.Td>
              <div style={{ background: `var(--mantine-color-${color}-filled)`, height: 12, width: `${(b.share / max) * 100}%`, minWidth: b.value ? 2 : 0, borderRadius: 2 }} />
            </Table.Td>
            <Table.Td w={1} style={{ whiteSpace: "nowrap" }}>{b.value} ({(b.share * 100).toFixed(0)}%)</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

export function StatsPanel({ yaml }: { yaml: string }) {
  const stats = useSheetStats();
  const [mode, setMode] = useState<"actual" | "sample">("actual");
  const [samples, setSamples] = useState(2000);
  const [seed, setSeed] = useState(0);
  const slots = useMemo(() => (stats.data ? slotSummaries(stats.data) : []), [stats.data]);
  return (
    <Stack gap="sm">
      <Text size="sm" c="dimmed">Runs only the task selection (no instance generation) and shows whether the slots and budget actually randomize the variants.</Text>
      <Group gap="xs" align="flex-end">
        <SegmentedControl size="xs" value={mode} onChange={(v) => setMode(v as "actual" | "sample")}
          data={[{ value: "actual", label: "this sheet's variants" }, { value: "sample", label: "simulate N" }]} />
        {mode === "sample" && <NumberInput size="xs" label="N" value={samples} min={1} max={20000} w={100} onChange={(v) => setSamples(Number(v) || 1)} />}
        <NumberInput size="xs" label="seed" value={seed} w={100} onChange={(v) => setSeed(Number(v) || 0)} />
        <Button size="xs" onClick={() => stats.mutate({ yaml, seed, samples: mode === "sample" ? samples : null })} loading={stats.isPending}>Compute</Button>
      </Group>
      <ErrorAlert error={stats.error} />
      {stats.data && (
        <>
          <SimpleGrid cols={4}>
            <Stat label="variants" value={stats.data.variants} />
            <Stat label="distinct task combinations" value={stats.data.distinct_combinations} />
            <Stat label="max repeats of one combination" value={stats.data.max_repeats} />
            <Stat label="family collisions avoided" value={stats.data.family_skips} />
          </SimpleGrid>
          <div>
            <Text fw={600} size="sm">Total complexity per variant (mean {mean(stats.data.total_complexity).toFixed(2)})</Text>
            <Bars bars={histogram(stats.data.total_complexity)} color="grape" />
          </div>
          {slots.map((s, i) => (
            <div key={i}>
              <Group gap="xs">
                <Text fw={600} size="sm">{i + 1}. {s.title}</Text>
                <Text size="xs" c={s.evenness < 0.6 ? "orange" : "dimmed"}>evenness {(s.evenness * 100).toFixed(0)}%</Text>
                {s.unused.length > 0 && <Text size="xs" c="orange">never chosen: {s.unused.join(", ")}</Text>}
              </Group>
              <Bars bars={s.bars.map((b) => ({ ...b, label: `${b.label} (c=${b.complexity})` }))} />
            </div>
          ))}
        </>
      )}
    </Stack>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <Text size="xl" fw={700}>{value}</Text>
      <Text size="xs" c="dimmed">{label}</Text>
    </div>
  );
}
