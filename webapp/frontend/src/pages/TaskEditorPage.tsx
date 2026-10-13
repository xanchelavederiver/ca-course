import {
  ActionIcon, Alert, Anchor, Badge, Box, Button, Code, Group, Loader, NumberInput, SegmentedControl, Select, Spoiler,
  Stack, Switch, Table, Tabs, Text, TextInput, Textarea, Title, Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconArrowsShuffle, IconDeviceFloppy, IconGitCompare, IconPlayerPlay } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { get } from "../api/client";
import { usePreview, useSaveTaskMeta, useSaveTaskSource, useTask, useValidateTask } from "../api/hooks";
import type { MetaFieldName, TaskDetail, ValidationResult } from "../api/types";
import { CodeEditor, DiffView } from "../components/CodeEditor";
import { ErrorAlert } from "../components/ErrorAlert";
import { InstanceCard } from "../components/InstanceCard";
import { PdfViewer } from "../components/PdfViewer";
import { TopicPicker } from "../components/Pickers";
import { json } from "../lib/format";
import { useDebounced, useUnsavedGuard } from "../lib/hooks";

type Drafts = Partial<Record<MetaFieldName, unknown>>;

const randomSeed = () => Math.floor(Math.random() * 2 ** 31);

export function TaskEditorPage() {
  const { id = "" } = useParams();
  const { data, error, isLoading } = useTask(id);
  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error ?? new Error("not found")} />;
  return <TaskEditor key={id} detail={data} />;
}

function TaskEditor({ detail }: { detail: TaskDetail }) {
  const nav = useNavigate();
  const id = detail.id;
  const meta = detail.meta;
  const info = detail.info;
  const [tab, setTab] = useState<string | null>(meta ? "meta" : "code");
  const [drafts, setDrafts] = useState<Drafts>({});
  const [code, setCode] = useState(detail.source);
  const [showDiff, setShowDiff] = useState(false);
  const saveMeta = useSaveTaskMeta(id);
  const saveSource = useSaveTaskSource(id);

  // a save elsewhere (metadata) changes the source: follow it unless the code has local edits
  const [baseSource, setBaseSource] = useState(detail.source);
  useEffect(() => {
    if (detail.source !== baseSource) {
      if (code === baseSource) setCode(detail.source);
      setBaseSource(detail.source);
    }
  }, [detail.source, baseSource, code]);

  const codeDirty = code !== detail.source;
  const metaDirty = Object.keys(drafts).length > 0;
  useUnsavedGuard(codeDirty || metaDirty);

  const fieldValue = (f: MetaFieldName): unknown => (f in drafts ? drafts[f] : meta?.fields[f]?.value);
  const setField = (f: MetaFieldName, v: unknown) =>
    setDrafts((d) => {
      const next = { ...d };
      if (JSON.stringify(v) === JSON.stringify(meta?.fields[f]?.value)) delete next[f];
      else next[f] = v;
      return next;
    });

  const save = useCallback(async () => {
    try {
      if (codeDirty) {
        if (metaDirty) {
          notifications.show({ color: "orange", message: "Save or discard the code edits before the form edits." });
          return;
        }
        const r = await saveSource.mutateAsync(code);
        notifications.show(r.ok
          ? { color: "green", message: "Saved module; the engine reloads it." }
          : { color: "orange", message: `Saved with a syntax error: ${r.syntax_error}` });
      } else if (metaDirty) {
        const r = await saveMeta.mutateAsync(drafts as Record<string, unknown>);
        setDrafts({});
        notifications.show({ color: "green", message: "Saved metadata." });
        if (r.id !== id) nav(`/tasks/${encodeURIComponent(r.id)}`, { replace: true });
      }
    } catch (e) {
      notifications.show({ color: "red", title: "Save failed", message: (e as Error).message });
    }
  }, [codeDirty, metaDirty, code, drafts, saveSource, saveMeta, id, nav]);

  return (
    <Stack gap="xs" h="calc(100vh - 80px)">
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Group gap="xs">
            <Title order={4} ff="monospace">{id}</Title>
            {info && <Text c="dimmed">{info.title}</Text>}
            {(codeDirty || metaDirty) && <Badge color="orange" variant="light">unsaved</Badge>}
          </Group>
          <Text size="xs" c="dimmed">{detail.file}:{meta?.line ?? ""} · class {detail.class_name}
            {meta && meta.bases.length > 0 && ` (${meta.bases.join(", ")})`}</Text>
        </div>
        <Group gap="xs">
          {(codeDirty || metaDirty) && (
            <Button size="xs" variant="default" onClick={() => { setDrafts({}); setCode(detail.source); }}>Discard</Button>
          )}
          <Button size="xs" leftSection={<IconDeviceFloppy size={14} />} onClick={save}
            disabled={!codeDirty && !metaDirty} loading={saveMeta.isPending || saveSource.isPending}>
            Save <Text span size="xs" c="dimmed" ml={4}>Ctrl+S</Text>
          </Button>
        </Group>
      </Group>

      {detail.import_error && (
        <Alert color="red" title="The module does not import" p="xs">
          <Spoiler maxHeight={40} showLabel="more" hideLabel="less">
            <Code block style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>{detail.import_error}</Code>
          </Spoiler>
        </Alert>
      )}
      {detail.meta_error && <Alert color="orange" p="xs">Metadata form unavailable: {detail.meta_error}</Alert>}

      <Group align="stretch" wrap="nowrap" gap="md" style={{ flex: 1, minHeight: 0 }}>
        <Stack style={{ flex: 1, minWidth: 0 }} gap={0}>
          <Tabs value={tab} onChange={setTab} keepMounted={false}>
            <Tabs.List>
              <Tabs.Tab value="meta" disabled={!meta}>Metadata</Tabs.Tab>
              <Tabs.Tab value="statement" disabled={!meta}>Statement{"statement" in drafts ? " •" : ""}</Tabs.Tab>
              <Tabs.Tab value="solution" disabled={!meta}>Solution{"solution" in drafts ? " •" : ""}</Tabs.Tab>
              <Tabs.Tab value="code">Code{codeDirty ? " •" : ""}</Tabs.Tab>
            </Tabs.List>
          </Tabs>
          <Box style={{ flex: 1, minHeight: 0, overflow: "auto" }} pt="xs">
            {tab === "meta" && meta && (
              <MetaForm detail={detail} value={fieldValue} set={setField} onCode={() => setTab("code")} disabled={codeDirty} />
            )}
            {(tab === "statement" || tab === "solution") && meta && (
              <TemplateEditor detail={detail} field={tab} value={fieldValue(tab) as string | undefined}
                onChange={(v) => setField(tab, v)} onSave={save} onCode={() => setTab("code")} disabled={codeDirty} />
            )}
            {tab === "code" && (
              <Stack gap={4} h="100%">
                <Group gap="xs">
                  <Switch size="xs" label="diff vs HEAD" checked={showDiff} onChange={(e) => setShowDiff(e.currentTarget.checked)}
                    thumbIcon={<IconGitCompare size={10} />} />
                  {metaDirty && <Text size="xs" c="orange">form edits pending — save them before editing code</Text>}
                </Group>
                <Box style={{ flex: 1, minHeight: 400 }}>
                  {showDiff ? <HeadDiff path={detail.file} modified={code} /> : (
                    <CodeEditor language="python" value={code} onChange={setCode} onSave={save}
                      readOnly={metaDirty} revealLine={meta?.line ?? null} />
                  )}
                </Box>
              </Stack>
            )}
          </Box>
        </Stack>

        <Box style={{ flex: 1, minWidth: 0, overflow: "auto" }}>
          <PreviewPanel detail={detail} statement={drafts.statement as string | undefined} solution={drafts.solution as string | undefined} />
        </Box>
      </Group>
    </Stack>
  );
}

function HeadDiff({ path, modified }: { path: string; modified: string }) {
  const { data } = useQuery({ queryKey: ["head", path], queryFn: () => get<{ content: string | null }>(`/git/head?path=${encodeURIComponent(path)}`) });
  if (!data) return <Loader size="sm" />;
  if (data.content === null) return <Text c="dimmed" size="sm">Not in HEAD (new file).</Text>;
  return <DiffView original={data.content} modified={modified} language="python" />;
}

function Computed({ expr, onCode, children }: { expr: string | null; onCode: () => void; children?: React.ReactNode }) {
  return (
    <Stack gap={2}>
      <Group gap={6}>
        <Badge size="xs" color="gray">computed in code</Badge>
        <Anchor size="xs" onClick={onCode}>edit in Code tab</Anchor>
      </Group>
      {expr && <Code style={{ fontSize: 11 }}>{expr.length > 200 ? expr.slice(0, 200) + "…" : expr}</Code>}
      {children}
    </Stack>
  );
}

function MetaForm({ detail, value, set, onCode, disabled }: {
  detail: TaskDetail; value: (f: MetaFieldName) => unknown; set: (f: MetaFieldName, v: unknown) => void;
  onCode: () => void; disabled: boolean;
}) {
  const fields = detail.meta!.fields;
  const info = detail.info;
  const editable = (f: MetaFieldName) => fields[f].editable && !disabled;
  const inherited = (f: MetaFieldName) => !fields[f].defined;
  const [presetsText, setPresetsText] = useState(() => json(value("presets") ?? info?.preset_values ?? { default: {} }));
  const [presetsError, setPresetsError] = useState<string | null>(null);

  const label = (f: MetaFieldName, text: string) => (
    <Group gap={4}>{text}{inherited(f) && <Badge size="xs" variant="outline" color="gray">inherited</Badge>}</Group>
  );

  return (
    <Stack gap="sm" maw={720}>
      <TextInput label={label("id", "Task id")} description="Stable slug: renaming breaks sheets and archived references."
        value={String(value("id") ?? "")} onChange={(e) => set("id", e.currentTarget.value)} disabled={!editable("id")} />
      {fields.title_ru.editable ? (
        <TextInput label={label("title_ru", "Title")} value={String(value("title_ru") ?? "")}
          onChange={(e) => set("title_ru", e.currentTarget.value)} disabled={disabled} />
      ) : <Computed expr={fields.title_ru.expr} onCode={onCode}><Text size="sm">{info?.title}</Text></Computed>}
      {fields.topics.editable ? (
        <TopicPicker label="Topics" value={(value("topics") as string[] | null) ?? info?.topics ?? []} onChange={(v) => set("topics", v)} />
      ) : <Computed expr={fields.topics.expr} onCode={onCode} />}
      <Group grow align="flex-start">
        {fields.complexity.editable ? (
          <NumberInput label={label("complexity", "Complexity")} description="spent against sheet budgets" min={1} max={10}
            value={(value("complexity") as number | null) ?? info?.complexity ?? 1} onChange={(v) => set("complexity", Number(v) || 1)} disabled={disabled} />
        ) : <Computed expr={fields.complexity.expr} onCode={onCode} />}
        {fields.family.editable ? (
          <TextInput label={label("family", "Family")} description={`tasks of one family never share a variant (now: ${info?.family_name ?? "—"})`}
            placeholder="(own id)" value={String(value("family") ?? "")} disabled={disabled}
            onChange={(e) => set("family", e.currentTarget.value || null)} />
        ) : <Computed expr={fields.family.expr} onCode={onCode} />}
      </Group>
      {fields.solution_detail.editable && (
        <div>
          <Text size="sm" fw={500}>{label("solution_detail", "Solution detail")}</Text>
          <SegmentedControl size="xs" data={[{ value: "full", label: "full (step-by-step)" }, { value: "answer_only", label: "answer only" }]}
            value={String(value("solution_detail") ?? info?.solution_detail ?? "answer_only")} onChange={(v) => set("solution_detail", v)} disabled={disabled} />
        </div>
      )}
      <div>
        <Text size="sm" fw={500}>{label("presets", "Presets (value-generation settings → self.cfg)")}</Text>
        {fields.presets.editable ? (
          <>
            <Text size="xs" c="dimmed">JSON; "default" is required, other presets override it. Unchanged values keep their Python expression (e.g. 10**6 + 1).</Text>
            <Box h={220} style={{ border: "1px solid var(--mantine-color-default-border)" }}>
              <CodeEditor language="json" value={presetsText} readOnly={disabled} onChange={(t) => {
                setPresetsText(t);
                try {
                  set("presets", JSON.parse(t));
                  setPresetsError(null);
                } catch (e) {
                  setPresetsError((e as Error).message);
                }
              }} />
            </Box>
            {presetsError && <Text size="xs" c="red">{presetsError}</Text>}
          </>
        ) : (
          <Computed expr={fields.presets.expr} onCode={onCode}>
            <Text size="xs" c="dimmed">Evaluated values:</Text>
            <Code block style={{ maxHeight: 220, overflow: "auto", fontSize: 11 }}>{json(info?.preset_values ?? {})}</Code>
          </Computed>
        )}
      </div>
      {fields.notes.editable ? (
        <Textarea label={label("notes", "Notes for maintainers")} autosize minRows={2} value={String(value("notes") ?? "")}
          onChange={(e) => set("notes", e.currentTarget.value)} disabled={disabled} />
      ) : <Computed expr={fields.notes.expr} onCode={onCode} />}
    </Stack>
  );
}

function TemplateEditor({ detail, field, value, onChange, onSave, onCode, disabled }: {
  detail: TaskDetail; field: "statement" | "solution"; value: string | undefined; onChange: (v: string) => void;
  onSave: () => void; onCode: () => void; disabled: boolean;
}) {
  const f = detail.meta!.fields[field];
  const effective = detail.info?.[field] ?? "";
  if (f.defined && !f.editable) {
    return (
      <Stack gap="xs" h="100%">
        <Computed expr={f.expr} onCode={onCode} />
        <Text size="xs" c="dimmed">Evaluated template (read-only):</Text>
        <Box style={{ flex: 1, minHeight: 300 }}><CodeEditor language="latex" value={effective} readOnly /></Box>
      </Stack>
    );
  }
  return (
    <Stack gap={4} h="100%">
      <Text size="xs" c="dimmed">
        Jinja2 with LaTeX-safe delimiters: <Code>{"\\VAR{expr}"}</Code>, <Code>{"\\BLOCK{for x in xs}…\\BLOCK{endfor}"}</Code>.
        The preview on the right re-renders as you type (unsaved).
        {!f.defined && " Inherited from a base class — saving adds it to this class."}
      </Text>
      <Box style={{ flex: 1, minHeight: 400 }}>
        <CodeEditor language="latex" value={value ?? effective} onChange={onChange} onSave={onSave} readOnly={disabled} />
      </Box>
    </Stack>
  );
}

function PreviewPanel({ detail, statement, solution }: { detail: TaskDetail; statement?: string; solution?: string }) {
  const presets = detail.info?.presets ?? ["default"];
  const [preset, setPreset] = useState<string>(presets[0]);
  const [seed, setSeed] = useState<number>(1);
  const [count, setCount] = useState<number>(3);
  const [tab, setTab] = useState<string | null>("preview");
  const [mode, setMode] = useState<"quick" | "pdf">("quick");
  const ref = preset === "default" ? detail.id : `${detail.id}@${preset}`;
  const preview = usePreview(ref);
  const pdf = usePreview(ref);
  const [pdfVersion, setPdfVersion] = useState(0);
  const validate = useValidateTask(detail.id);
  const [vcount, setVcount] = useState(50);

  const args = useMemo(() => ({ seed, count, statement: statement ?? null, solution: solution ?? null }), [seed, count, statement, solution]);
  const debounced = useDebounced(args, 600);
  const { mutate } = preview;
  useEffect(() => {
    if (detail.info) mutate(debounced);
  }, [debounced, ref, mutate, detail.info, detail.source]);

  if (!detail.info) return <Alert color="gray">Preview unavailable: {detail.info_error ?? "task not loaded"}</Alert>;

  const buildPdf = async () => {
    setPdfVersion(Date.now());
    await pdf.mutateAsync({ ...args, pdf: true });
  };

  return (
    <Tabs value={tab} onChange={setTab}>
      <Tabs.List>
        <Tabs.Tab value="preview">Preview</Tabs.Tab>
        <Tabs.Tab value="validate">Validate</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="preview" pt="xs">
        <Group gap="xs" align="flex-end" mb="xs">
          <Select size="xs" label="preset" data={presets} value={preset} onChange={(v) => v && setPreset(v)} w={110} />
          <NumberInput size="xs" label="seed" value={seed} onChange={(v) => setSeed(Number(v) || 0)} w={130} min={0}
            rightSection={<Tooltip label="random seed"><ActionIcon size="sm" variant="subtle" onClick={() => setSeed(randomSeed())}>
              <IconArrowsShuffle size={14} /></ActionIcon></Tooltip>} />
          <NumberInput size="xs" label="instances" value={count} onChange={(v) => setCount(Math.max(1, Math.min(20, Number(v) || 1)))} w={80} min={1} max={20} />
          <SegmentedControl size="xs" value={mode} onChange={(v) => setMode(v as "quick" | "pdf")}
            data={[{ value: "quick", label: "Quick (MathJax)" }, { value: "pdf", label: "PDF" }]} />
          {preview.isPending && <Loader size="xs" />}
        </Group>
        {(statement !== undefined || solution !== undefined) && <Text size="xs" c="orange" mb={4}>Showing unsaved template edits.</Text>}
        {mode === "quick" ? (
          <Stack gap="xs">
            <ErrorAlert error={preview.error} />
            {preview.data?.instances.map((inst, i) => <InstanceCard key={`${inst.seed}-${i}`} inst={inst} index={i} />)}
          </Stack>
        ) : (
          <Stack gap="xs">
            <Group gap="xs">
              <Button size="xs" leftSection={<IconPlayerPlay size={14} />} onClick={buildPdf} loading={pdf.isPending}>Build PDF</Button>
              <Text size="xs" c="dimmed">canonical rendering via pdfLaTeX (ca-sheet class)</Text>
            </Group>
            <ErrorAlert error={pdf.error} />
            {pdf.data?.log && !pdf.data.pdf && <Code block style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>{pdf.data.log}</Code>}
            {pdf.data?.pdf && <PdfViewer path={pdf.data.pdf} version={pdfVersion} height="65vh" />}
          </Stack>
        )}
      </Tabs.Panel>
      <Tabs.Panel value="validate" pt="xs">
        <Group gap="xs" align="flex-end" mb="xs">
          <NumberInput size="xs" label="instances per preset" value={vcount} onChange={(v) => setVcount(Number(v) || 1)} w={150} min={1} max={1000} />
          <Button size="xs" onClick={() => validate.mutate(vcount)} loading={validate.isPending}>Validate</Button>
        </Group>
        <ErrorAlert error={validate.error} />
        {validate.data && (
          <ValidationTable result={validate.data} onSeed={(r, s) => {
            setPreset(r.includes("@") ? r.split("@")[1] : "default");
            setSeed(s);
            setCount(1);
            setTab("preview");
          }} />
        )}
        {!validate.data && detail.validation && (
          <Text size="sm" c="dimmed">Last run: {detail.validation.ok ? "ok" : "failed"} ({detail.validation.count} instances).</Text>
        )}
        <Text size="xs" c="dimmed" mt="sm">
          Each instance is generated twice from its seed: self-check (<Code>check()</Code>), LaTeX sanity and determinism.
          Click a failing seed to open it in the preview. See also <Anchor component={Link} to="/tasks">all tasks</Anchor>.
        </Text>
      </Tabs.Panel>
    </Tabs>
  );
}

function ValidationTable({ result, onSeed }: { result: ValidationResult; onSeed: (ref: string, seed: number) => void }) {
  return (
    <Table fz="sm" verticalSpacing={4}>
      <Table.Thead><Table.Tr><Table.Th>preset</Table.Th><Table.Th>result</Table.Th><Table.Th>failing seed</Table.Th></Table.Tr></Table.Thead>
      <Table.Tbody>
        {result.results.map((r) => (
          <Table.Tr key={r.ref}>
            <Table.Td ff="monospace">{r.ref}</Table.Td>
            <Table.Td>
              {r.ok ? <Badge color="green" variant="light">ok</Badge> : (
                <Stack gap={2}>
                  <Text size="sm" c="red">{r.error}</Text>
                  {r.traceback && (
                    <Spoiler maxHeight={0} showLabel="traceback" hideLabel="hide">
                      <Code block style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>{r.traceback}</Code>
                    </Spoiler>
                  )}
                </Stack>
              )}
            </Table.Td>
            <Table.Td>{r.seed != null && !r.ok && <Anchor size="sm" onClick={() => onSeed(r.ref, r.seed!)}>{r.seed}</Anchor>}</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
