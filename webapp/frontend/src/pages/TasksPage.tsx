import {
  Alert, Anchor, Badge, Button, Chip, Code, Drawer, Group, Modal, NavLink, NumberInput, ScrollArea, Select, Spoiler,
  Stack, Table, Text, TextInput, Title, Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconCheck, IconPlus, IconSearch, IconX } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError, post } from "../api/client";
import { keys, useTasks, useTopics } from "../api/hooks";
import type { TaskSummary } from "../api/types";
import { ErrorAlert } from "../components/ErrorAlert";
import { JobLog } from "../components/JobLog";
import { useTopicOptions } from "../components/Pickers";
import { ago } from "../lib/format";

function topicMatch(task: TaskSummary, topic: string | null): boolean {
  return !topic || task.topics.some((t) => t === topic || t.startsWith(topic + "."));
}

export function ValidationBadge({ task }: { task: TaskSummary }) {
  if (task.broken) return <Badge color="red" leftSection={<IconAlertTriangle size={12} />}>import error</Badge>;
  const v = task.validation;
  if (!v) return <Text size="xs" c="dimmed">—</Text>;
  return (
    <Tooltip label={`${v.count} instances/preset, ${ago(v.at)}`}>
      <Badge color={v.ok ? "green" : "red"} variant="light" leftSection={v.ok ? <IconCheck size={12} /> : <IconX size={12} />}>
        {v.ok ? "ok" : "failed"}
      </Badge>
    </Tooltip>
  );
}

export function TasksPage() {
  const { data, error, isLoading } = useTasks();
  const { data: topics } = useTopics();
  const [params, setParams] = useSearchParams();
  const topic = params.get("topic");
  const [text, setText] = useState("");
  const [complexity, setComplexity] = useState<string[]>([]);
  const [newOpen, newCtl] = useDisclosure(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [count, setCount] = useState<number>(20);

  const tasks = useMemo(() => {
    const q = text.toLowerCase();
    return (data?.tasks ?? []).filter((t) =>
      topicMatch(t, topic) &&
      (!complexity.length || (t.complexity != null && complexity.includes(String(t.complexity)))) &&
      (!q || t.id.toLowerCase().includes(q) || t.title.toLowerCase().includes(q) || (t.family ?? "").includes(q)));
  }, [data, topic, text, complexity]);

  const importErrors = Object.entries(data?.import_errors ?? {});
  const syntaxErrors = Object.entries(data?.syntax_errors ?? {});

  return (
    <Group align="flex-start" wrap="nowrap" gap="md">
      <ScrollArea w={260} h="calc(100vh - 90px)" style={{ flexShrink: 0 }}>
        <Text size="xs" fw={600} c="dimmed" mb={4}>TOPICS</Text>
        <NavLink label={`All (${data?.tasks.length ?? 0})`} active={!topic} onClick={() => setParams({})} />
        {(topics ?? []).map((t) => (
          <NavLink key={t.slug} active={topic === t.slug} onClick={() => setParams({ topic: t.slug })}
            pl={8 + t.depth * 14} py={3}
            label={<Text size="sm">{t.title}</Text>}
            description={t.slug} rightSection={<Badge size="xs" variant="light">{t.count}</Badge>} />
        ))}
      </ScrollArea>

      <Stack style={{ flex: 1, minWidth: 0 }} gap="sm">
        <Group justify="space-between">
          <Title order={3}>Tasks</Title>
          <Group gap="xs">
            <NumberInput size="xs" w={90} min={1} max={500} value={count} onChange={(v) => setCount(Number(v) || 1)}
              rightSection={<Text size="xs" c="dimmed" pr={6}>×</Text>} aria-label="instances per task" />
            <Button size="xs" variant="light" onClick={async () => setJobId((await post<{ job: string }>("/validate", { count })).job)}>
              Validate all
            </Button>
            <Button size="xs" leftSection={<IconPlus size={14} />} onClick={newCtl.open}>New task</Button>
          </Group>
        </Group>

        {importErrors.length > 0 && (
          <Alert color="red" title="Task modules that do not import" icon={<IconAlertTriangle />}>
            <Stack gap={4}>
              {importErrors.map(([mod, tb]) => {
                const path = mod.replace(/\./g, "/") + ".py";
                return (
                  <div key={mod}>
                    <Anchor component={Link} to={`/modules?path=${encodeURIComponent(path)}`}>{path}</Anchor>
                    <Spoiler maxHeight={0} showLabel="traceback" hideLabel="hide">
                      <Code block style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>{tb}</Code>
                    </Spoiler>
                  </div>
                );
              })}
              {syntaxErrors.map(([path, msg]) => (
                <Text key={path} size="sm">
                  <Anchor component={Link} to={`/modules?path=${encodeURIComponent(path)}`}>{path}</Anchor>: {msg}
                </Text>
              ))}
            </Stack>
          </Alert>
        )}

        <Group gap="xs">
          <TextInput size="xs" placeholder="search id, title, family" leftSection={<IconSearch size={14} />}
            value={text} onChange={(e) => setText(e.currentTarget.value)} w={260} />
          <Text size="xs" c="dimmed">complexity</Text>
          <Chip.Group multiple value={complexity} onChange={setComplexity}>
            {["1", "2", "3"].map((c) => <Chip key={c} value={c} size="xs">{c}</Chip>)}
          </Chip.Group>
          <Text size="xs" c="dimmed">{tasks.length} shown</Text>
        </Group>

        <ErrorAlert error={error} />
        {isLoading && <Text c="dimmed">Loading tasks (the engine imports Sage on first start)…</Text>}
        <Table striped highlightOnHover stickyHeader verticalSpacing={4} fz="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>id</Table.Th><Table.Th>title</Table.Th><Table.Th>topics</Table.Th>
              <Table.Th>c</Table.Th><Table.Th>family</Table.Th><Table.Th>presets</Table.Th><Table.Th>validation</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {tasks.map((t) => (
              <Table.Tr key={t.id}>
                <Table.Td><Anchor component={Link} to={`/tasks/${encodeURIComponent(t.id)}`} ff="monospace" size="sm">{t.id}</Anchor></Table.Td>
                <Table.Td>{t.title}</Table.Td>
                <Table.Td>{t.topics.map((x) => <Badge key={x} size="xs" variant="outline" mr={2}>{x}</Badge>)}</Table.Td>
                <Table.Td>{t.complexity ?? "—"}</Table.Td>
                <Table.Td><Text size="xs" c="dimmed">{t.family ?? ""}</Text></Table.Td>
                <Table.Td>{t.presets.map((p) => <Badge key={p} size="xs" color="gray" variant="light" mr={2}>{p}</Badge>)}</Table.Td>
                <Table.Td><ValidationBadge task={t} /></Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Stack>

      <NewTaskModal opened={newOpen} onClose={newCtl.close} initialTopic={topic} />
      <Drawer opened={!!jobId} onClose={() => setJobId(null)} position="right" size="lg" title="Validation">
        <JobLog jobId={jobId}>
          {(r: { ok: boolean; results: { ref: string; ok: boolean; error: string | null }[]; taxonomy: string[] }) => (
            <Stack gap={4}>
              <Alert color={r.ok ? "green" : "red"}>{r.ok ? "All tasks valid" : "Some tasks failed"}</Alert>
              {r.taxonomy.map((p) => <Text key={p} c="red" size="sm">{p}</Text>)}
              {r.results.filter((x) => !x.ok).map((x) => (
                <Text key={x.ref} size="sm">
                  <Anchor component={Link} to={`/tasks/${encodeURIComponent(x.ref.split("@")[0])}`}>{x.ref}</Anchor>: {x.error}
                </Text>
              ))}
            </Stack>
          )}
        </JobLog>
      </Drawer>
    </Group>
  );
}

function slug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function NewTaskModal({ opened, onClose, initialTopic }: { opened: boolean; onClose: () => void; initialTopic: string | null }) {
  const topicOptions = useTopicOptions();
  const { data: tasks } = useTasks();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [topic, setTopic] = useState<string | null>(initialTopic);
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [className, setClassName] = useState("");
  const [module, setModule] = useState<string | null>(null);
  const [newModule, setNewModule] = useState("");
  const [complexity, setComplexity] = useState<number>(1);
  const [err, setErr] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const root = topic?.split(".")[0] ?? "";
  const modules = useMemo(() => {
    const files = new Set((tasks?.tasks ?? []).map((t) => t.file).filter((f): f is string => !!f && f.startsWith(`taskgen/tasks/${root}/`)));
    return [...files].map((f) => f.replace("taskgen/tasks/", ""));
  }, [tasks, root]);
  const moduleValue = module === "__new__" || !module ? `${root}/${slug(newModule || name) || "new_tasks"}.py` : module;
  const taskId = root && name ? `${root}.${slug(name)}` : "";
  const cls = className || name.split(/[^A-Za-z0-9]+/).filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join("");

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await post<{ id: string }>("/tasks", {
        task_id: taskId, class_name: cls, title, topic, complexity, module: moduleValue,
      });
      notifications.show({ color: "green", message: `Created ${r.id}` });
      qc.invalidateQueries({ queryKey: keys.tasks });
      onClose();
      nav(`/tasks/${encodeURIComponent(r.id)}`);
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="New task" size="lg">
      <Stack gap="sm">
        <Select label="Topic" data={topicOptions} value={topic} onChange={setTopic} searchable required />
        <TextInput label="Short name (Latin)" description="becomes the id suffix and the class name" placeholder="e.g. baby giant"
          value={name} onChange={(e) => setName(e.currentTarget.value)} required />
        <TextInput label="Title (Russian)" value={title} onChange={(e) => setTitle(e.currentTarget.value)} required />
        <Group grow>
          <TextInput label="Task id" value={taskId} readOnly description="stable — never rename once issued" />
          <TextInput label="Class name" value={cls} onChange={(e) => setClassName(e.currentTarget.value)} />
        </Group>
        <Group grow align="flex-end">
          <Select label="Module" data={[...modules.map((m) => ({ value: m, label: m })), { value: "__new__", label: "new module…" }]}
            value={module ?? "__new__"} onChange={setModule} />
          {(module === "__new__" || !module) && (
            <TextInput label="New module name" placeholder={slug(name) || "new_tasks"} value={newModule}
              onChange={(e) => setNewModule(e.currentTarget.value)} />
          )}
        </Group>
        <Text size="xs" c="dimmed">File: taskgen/tasks/{moduleValue}</Text>
        <NumberInput label="Complexity" min={1} max={10} value={complexity} onChange={(v) => setComplexity(Number(v) || 1)} w={140} />
        {err instanceof ApiError || err ? <ErrorAlert error={err} /> : null}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} loading={busy} disabled={!taskId || !title || !topic || !cls}>Create</Button>
        </Group>
      </Stack>
    </Modal>
  );
}
