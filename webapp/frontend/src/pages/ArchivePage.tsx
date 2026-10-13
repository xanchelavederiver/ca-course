import {
  Alert, Anchor, Badge, Button, Code, Group, Loader, MultiSelect, Select, SimpleGrid, Stack, Table, Tabs, Text, TextInput, Title,
} from "@mantine/core";
import { IconCheck, IconShieldCheck, IconX } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { post } from "../api/client";
import { useArchive, useRun } from "../api/hooks";
import type { RegenResult, RunDetail } from "../api/types";
import { ErrorAlert } from "../components/ErrorAlert";
import { JobLog } from "../components/JobLog";
import { PdfViewer } from "../components/PdfViewer";
import { ago, json, shortSha } from "../lib/format";

export function ArchivePage() {
  const { data, error, isLoading } = useArchive();
  return (
    <Stack gap="md">
      <div>
        <Title order={3}>Archive</Title>
        <Text size="sm" c="dimmed">Issued runs (archive/&lt;sheet&gt;/&lt;run&gt;/): manifest, sources and sealed PDFs. Commit them.</Text>
      </div>
      <ErrorAlert error={error} />
      {isLoading && <Loader />}
      {data?.length === 0 && <Text c="dimmed">Nothing issued yet. Issue a sheet from its editor.</Text>}
      {data?.map((s) => (
        <div key={s.sheet_id}>
          <Text fw={600} ff="monospace" mb={4}>{s.sheet_id}</Text>
          <Table striped fz="sm" verticalSpacing={4}>
            <Table.Thead>
              <Table.Tr><Table.Th>run</Table.Th><Table.Th>created</Table.Th><Table.Th>master seed</Table.Th><Table.Th>variants</Table.Th>
                <Table.Th>engine</Table.Th><Table.Th>commit</Table.Th><Table.Th>PDFs</Table.Th></Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {s.runs.map((r) => (
                <Table.Tr key={r.run}>
                  <Table.Td><Anchor component={Link} to={`/archive/${s.sheet_id}/${r.run}`} ff="monospace">{r.run}</Anchor></Table.Td>
                  <Table.Td>{ago(r.created_at)}</Table.Td>
                  <Table.Td ff="monospace">{r.master_seed}</Table.Td>
                  <Table.Td>{r.variants}</Table.Td>
                  <Table.Td>{r.engine_version}</Table.Td>
                  <Table.Td><Text span ff="monospace" size="sm">{shortSha(r.git?.commit)}</Text>
                    {r.git?.dirty && <Badge size="xs" color="orange" ml={4}>dirty</Badge>}</Table.Td>
                  <Table.Td>{r.sealed.length ? <Badge size="sm" color="green" variant="light">{r.sealed.length} sealed</Badge>
                    : <Badge size="sm" color="red" variant="light">not sealed</Badge>}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      ))}
    </Stack>
  );
}

export function RunPage() {
  const { sheet = "", run = "" } = useParams();
  const { data, error, isLoading } = useRun(sheet, run);
  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error} />;
  return <RunView run={data} />;
}

function RunView({ run }: { run: RunDetail }) {
  const m = run.manifest;
  const pdfs = run.files_on_disk.filter((f) => f.endsWith(".pdf"));
  const [pdf, setPdf] = useState<string | null>(pdfs[0] ?? null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [only, setOnly] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const variantKeys = useMemo(() => m.variants.map((v) => v.key), [m.variants]);

  const verify = async (variants: string[] | null) => {
    const r = await post<{ job: string }>(`/archive/${run.sheet_id}/${run.run}/regen`, { variants });
    setJobId(r.job);
  };

  const shown = m.variants.filter((v) => !filter || `${v.key} ${v.student ?? ""}`.toLowerCase().includes(filter.toLowerCase()));

  return (
    <Stack gap="sm">
      <Group justify="space-between">
        <div>
          <Title order={4} ff="monospace">archive/{run.sheet_id}/{run.run}</Title>
          <Text size="sm" c="dimmed">{m.spec_path} · created {ago(run.created_at)}</Text>
        </div>
      </Group>
      <SimpleGrid cols={{ base: 2, md: 5 }}>
        <Field label="master seed" value={String(run.master_seed)} />
        <Field label="engine" value={run.engine_version} />
        <Field label="commit" value={`${shortSha(run.git?.commit)}${run.git?.dirty ? " (dirty tree)" : ""}`} />
        <Field label="variants" value={String(run.variants)} />
        <Field label="layout" value={run.layout} />
      </SimpleGrid>
      {run.git?.dirty && <Alert color="orange" p="xs">Issued from a working tree with uncommitted changes: the commit does not fully describe the generator.</Alert>}

      <Tabs defaultValue="pdfs">
        <Tabs.List>
          <Tabs.Tab value="pdfs">PDFs</Tabs.Tab>
          <Tabs.Tab value="variants">Students &amp; answers</Tabs.Tab>
          <Tabs.Tab value="verify">Verify</Tabs.Tab>
          <Tabs.Tab value="manifest">Manifest</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="pdfs" pt="xs">
          {pdfs.length === 0 ? <Text c="dimmed">No PDFs in this run.</Text> : (
            <Stack gap="xs">
              <Select data={pdfs.map((p) => ({ value: p, label: `${p}${m.files[p] ? " ✓ sealed" : ""}` }))} value={pdf} onChange={setPdf} w={400} />
              {pdf && <PdfViewer path={`${run.path}/${pdf}`} />}
            </Stack>
          )}
        </Tabs.Panel>
        <Tabs.Panel value="variants" pt="xs">
          <TextInput size="xs" placeholder="filter by key or student" value={filter} onChange={(e) => setFilter(e.currentTarget.value)} w={300} mb="xs" />
          <Table fz="xs" striped verticalSpacing={2}>
            <Table.Thead><Table.Tr><Table.Th>variant</Table.Th><Table.Th>student</Table.Th><Table.Th>tasks → answers</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {shown.map((v) => (
                <Table.Tr key={v.key}>
                  <Table.Td ff="monospace">{v.key}</Table.Td>
                  <Table.Td>{v.student ?? "—"}</Table.Td>
                  <Table.Td>
                    {v.tasks.map((t) => (
                      <div key={t.slot}>
                        <Text span size="xs" ff="monospace">{t.slot + 1}. {t.task}{t.preset !== "default" ? `@${t.preset}` : ""}</Text>
                        <Text span size="xs" c="dimmed"> → {JSON.stringify(t.answer).slice(0, 160)}</Text>
                      </div>
                    ))}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Tabs.Panel>
        <Tabs.Panel value="verify" pt="xs">
          <Stack gap="xs" maw={900}>
            <Text size="sm">Regenerate from the manifest alone (spec snapshot + master seed) and compare byte-for-byte.</Text>
            <Group gap="xs" align="flex-end">
              <Button leftSection={<IconShieldCheck size={16} />} onClick={() => verify(null)}>Verify all</Button>
              <MultiSelect label="or single variants" data={variantKeys} value={only} onChange={setOnly} searchable w={320} limit={100} />
              <Button variant="light" disabled={!only.length} onClick={() => verify(only)}>Regenerate selected</Button>
            </Group>
            <JobLog<RegenResult> jobId={jobId}>
              {(r) => (
                <Alert color={r.identical ? "green" : "red"} icon={r.identical ? <IconCheck /> : <IconX />}
                  title={r.identical ? "IDENTICAL" : `DIFFERENT: ${r.mismatches.join(", ")}`}>
                  <Text size="sm">{r.checked.length} variant(s) checked; output in <Code>{r.out_dir}</Code>.</Text>
                  {r.warnings.map((w) => <Text key={w} size="sm" c="orange">warning: {w}</Text>)}
                </Alert>
              )}
            </JobLog>
          </Stack>
        </Tabs.Panel>
        <Tabs.Panel value="manifest" pt="xs">
          <Code block style={{ fontSize: 11, maxHeight: "70vh", overflow: "auto" }}>{json({ ...m, variants: `[${m.variants.length} variants]` })}</Code>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Text size="xs" c="dimmed">{label}</Text>
      <Text size="sm" ff="monospace">{value}</Text>
    </div>
  );
}
