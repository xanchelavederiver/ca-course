import { Alert, Badge, Box, Button, Group, List, Loader, NumberInput, Stack, Tabs, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy, IconFileTypePdf, IconSend } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError, enc, post, put } from "../api/client";
import { keys, useSheet } from "../api/hooks";
import type { GenResult, SheetDetail } from "../api/types";
import { CodeEditor } from "../components/CodeEditor";
import { ErrorAlert } from "../components/ErrorAlert";
import { JobLog } from "../components/JobLog";
import { SheetFormView } from "../components/SheetForm";
import { DraftView, IssueDialog, StatsPanel, type RunFiles } from "../components/SheetRun";
import { useDebounced, useUnsavedGuard } from "../lib/hooks";
import { dataToForm, formToData, parseYaml, variantCount, type SheetForm } from "../lib/sheet";
import { KindBadge } from "./SheetsPage";

export function SheetEditorPage() {
  const splat = useParams()["*"] ?? "";
  const path = `sheets/${splat}`;
  const { data, error, isLoading } = useSheet(path);
  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error} />;
  return <SheetEditor key={path} detail={data} />;
}

function SheetEditor({ detail }: { detail: SheetDetail }) {
  const qc = useQueryClient();
  const [saved, setSaved] = useState(detail.raw);
  const [raw, setRaw] = useState(detail.raw);
  const [form, setForm] = useState<SheetForm>(() => dataToForm(detail.data));
  const [pendingForm, setPendingForm] = useState<SheetForm | null>(null);
  const [tab, setTab] = useState<string | null>("form");
  const [problems, setProblems] = useState<string[]>(detail.problems);
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<unknown>(null);
  const [draftJob, setDraftJob] = useState<string | null>(null);
  const [draftSeed, setDraftSeed] = useState<number | "">("");
  const [draft, setDraft] = useState<{ run: RunFiles; version: number } | null>(
    detail.draft ? { run: detail.draft, version: Date.parse(detail.draft.created_at ?? "") || 0 } : null);
  const [issueOpen, issueCtl] = useDisclosure(false);
  const rawRef = useRef(raw);
  rawRef.current = raw;

  const dirty = raw !== saved || pendingForm !== null;
  useUnsavedGuard(dirty);

  // form edits -> YAML text (server-side merge keeps comments and formatting)
  const flushForm = useCallback(async (f: SheetForm | null = pendingForm): Promise<string> => {
    if (!f) return rawRef.current;
    const base = rawRef.current;
    const data = formToData(f, parseYaml(base).data);
    const r = await post<{ raw: string }>("/sheets/merge", { base, data });
    setRaw(r.raw);
    rawRef.current = r.raw;
    setPendingForm((p) => (p === f ? null : p));
    return r.raw;
  }, [pendingForm]);

  const debouncedForm = useDebounced(pendingForm, 400);
  useEffect(() => {
    if (debouncedForm) flushForm(debouncedForm).catch((e) => setYamlError(String(e)));
  }, [debouncedForm]);

  const onForm = (f: SheetForm) => {
    setForm(f);
    setPendingForm(f);
  };

  const onYaml = (text: string) => {
    setRaw(text);
    const { data, error } = parseYaml(text);
    setYamlError(error);
    if (!error) setForm(dataToForm(data));
  };

  // live validation of the current text
  const debouncedRaw = useDebounced(raw, 500);
  useEffect(() => {
    let stale = false;
    post<{ problems: string[] }>("/sheets/validate", { yaml: debouncedRaw })
      .then((r) => !stale && setProblems(r.problems))
      .catch(() => {});
    return () => {
      stale = true;
    };
  }, [debouncedRaw]);

  const save = useCallback(async () => {
    setSaveError(null);
    try {
      const text = await flushForm();
      await put(`/sheets/${enc(detail.path)}`, { raw: text });
      setSaved(text);
      qc.invalidateQueries({ queryKey: keys.sheets });
      qc.invalidateQueries({ queryKey: keys.git });
      notifications.show({ color: "green", message: `Saved ${detail.path}` });
    } catch (e) {
      setSaveError(e);
      if (e instanceof ApiError && e.problems.length) setProblems(e.problems);
    }
  }, [flushForm, detail.path, qc]);

  const runDraft = async () => {
    const text = await flushForm();
    const r = await post<{ job: string }>("/runs/draft", { yaml: text, path: detail.path, seed: draftSeed === "" ? null : draftSeed });
    setDraftJob(r.job);
    setTab("draft");
  };

  const switchTab = async (t: string | null) => {
    if (t === "yaml" || t === "stats") await flushForm().catch(() => {});
    setTab(t);
  };

  const variants = variantCount(form);

  return (
    <Stack gap="xs">
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Group gap="xs">
            <Title order={4}>{form.title || detail.path}</Title>
            <KindBadge kind={form.kind} />
            {dirty && <Badge color="orange" variant="light">unsaved</Badge>}
          </Group>
          <Text size="xs" c="dimmed" ff="monospace">{detail.path} · id {form.id} · {variants} variant(s)</Text>
        </div>
        <Group gap="xs">
          <NumberInput size="xs" placeholder="random seed" value={draftSeed} onChange={(v) => setDraftSeed(v === "" ? "" : Number(v))} w={130} aria-label="draft seed" />
          <Button size="xs" variant="light" leftSection={<IconFileTypePdf size={14} />} onClick={runDraft} disabled={problems.length > 0}>Draft</Button>
          <Button size="xs" leftSection={<IconDeviceFloppy size={14} />} onClick={save} disabled={!dirty}>Save</Button>
          <Button size="xs" color="red" variant="light" leftSection={<IconSend size={14} />} onClick={issueCtl.open}>Issue…</Button>
        </Group>
      </Group>

      {problems.length > 0 && (
        <Alert color="red" p="xs" title="Invalid sheet (saving and drafting are blocked)">
          <List size="xs">{problems.map((p, i) => <List.Item key={i}>{p}</List.Item>)}</List>
        </Alert>
      )}
      {yamlError && <Alert color="red" p="xs">YAML: {yamlError}</Alert>}
      <ErrorAlert error={saveError} title="Not saved" />

      <Tabs value={tab} onChange={switchTab} keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="form">Form</Tabs.Tab>
          <Tabs.Tab value="yaml">YAML</Tabs.Tab>
          {form.kind === "individual" && <Tabs.Tab value="stats">Variant statistics</Tabs.Tab>}
          <Tabs.Tab value="draft">Draft PDFs{draftJob ? " •" : ""}</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="form" pt="sm">
          <Box maw={1000}><SheetFormView form={form} onChange={onForm} /></Box>
        </Tabs.Panel>
        <Tabs.Panel value="yaml" pt="sm">
          <Box h="calc(100vh - 260px)" style={{ border: "1px solid var(--mantine-color-default-border)" }}>
            <CodeEditor language="yaml" value={raw} onChange={onYaml} onSave={save} />
          </Box>
        </Tabs.Panel>
        <Tabs.Panel value="stats" pt="sm">
          <StatsPanel yaml={raw} />
        </Tabs.Panel>
        <Tabs.Panel value="draft" pt="sm">
          <Stack gap="xs">
            <JobLog<GenResult> jobId={draftJob} compact onDone={(j) => {
              const r = j.result;
              if (j.status === "done" && r) setDraft({ run: r, version: Date.now() });
            }}>
              {(r) => (r.warning ? <Alert color="orange" p="xs">{r.warning}</Alert> : null)}
            </JobLog>
            {draft ? <DraftView run={draft.run} version={draft.version} /> : !draftJob && (
              <Text c="dimmed" size="sm">No draft yet. “Draft” generates the sheet (with unsaved edits) into build/sheets/{form.id}/ — nothing is archived.</Text>
            )}
          </Stack>
        </Tabs.Panel>
      </Tabs>

      <IssueDialog opened={issueOpen} onClose={issueCtl.close} path={detail.path} variants={variants}
        unsaved={dirty} problems={problems} />
    </Stack>
  );
}
