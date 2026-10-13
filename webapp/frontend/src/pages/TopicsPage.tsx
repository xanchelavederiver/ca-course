import { ActionIcon, Badge, Button, Group, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconArrowDown, IconArrowUp, IconPlus, IconTrash } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { put } from "../api/client";
import { keys, useTopics } from "../api/hooks";
import type { Topic } from "../api/types";
import { ErrorAlert } from "../components/ErrorAlert";
import { useUnsavedGuard } from "../lib/hooks";
import { moveItem } from "../lib/sheet";

export function TopicsPage() {
  const { data, error } = useTopics();
  const qc = useQueryClient();
  const [rows, setRows] = useState<{ slug: string; title: string }[]>([]);
  const [err, setErr] = useState<unknown>(null);
  useEffect(() => setRows((data ?? []).map((t) => ({ slug: t.slug, title: t.title }))), [data]);
  const counts = new Map((data ?? []).map((t: Topic) => [t.slug, t.count]));
  const dirty = JSON.stringify(rows) !== JSON.stringify((data ?? []).map((t) => ({ slug: t.slug, title: t.title })));
  useUnsavedGuard(dirty);

  const save = async () => {
    setErr(null);
    try {
      const out = await put<Topic[]>("/topics", { items: rows });
      qc.setQueryData(keys.topics, out);
      qc.invalidateQueries({ queryKey: keys.tasks });
      notifications.show({ color: "green", message: "Saved taxonomy.yaml" });
    } catch (e) {
      setErr(e);
    }
  };

  const set = (i: number, k: "slug" | "title", v: string) => setRows((r) => r.map((x, j) => (j === i ? { ...x, [k]: v } : x)));

  return (
    <Stack gap="sm" maw={900}>
      <Group justify="space-between">
        <div>
          <Title order={3}>Topics</Title>
          <Text size="sm" c="dimmed">taskgen/tasks/taxonomy.yaml — dotted slugs; every prefix must be a topic too.</Text>
        </div>
        <Group gap="xs">
          {dirty && <Button size="xs" variant="default" onClick={() => setRows((data ?? []).map((t) => ({ slug: t.slug, title: t.title })))}>Discard</Button>}
          <Button size="xs" onClick={save} disabled={!dirty}>Save</Button>
        </Group>
      </Group>
      <ErrorAlert error={error ?? err} />
      <Table fz="sm" verticalSpacing={2}>
        <Table.Thead><Table.Tr><Table.Th>slug</Table.Th><Table.Th>title</Table.Th><Table.Th>tasks</Table.Th><Table.Th /></Table.Tr></Table.Thead>
        <Table.Tbody>
          {rows.map((r, i) => (
            <Table.Tr key={i}>
              <Table.Td><TextInput size="xs" ff="monospace" value={r.slug} onChange={(e) => set(i, "slug", e.currentTarget.value)}
                styles={{ input: { paddingLeft: 8 + r.slug.split(".").length * 10 - 10 } }} /></Table.Td>
              <Table.Td><TextInput size="xs" value={r.title} onChange={(e) => set(i, "title", e.currentTarget.value)} /></Table.Td>
              <Table.Td>{counts.has(r.slug) ? <Badge size="xs" variant="light">{counts.get(r.slug)}</Badge> : <Badge size="xs" color="gray">new</Badge>}</Table.Td>
              <Table.Td>
                <Group gap={2} wrap="nowrap">
                  <ActionIcon size="sm" variant="subtle" disabled={i === 0} onClick={() => setRows((x) => moveItem(x, i, i - 1))}><IconArrowUp size={14} /></ActionIcon>
                  <ActionIcon size="sm" variant="subtle" disabled={i === rows.length - 1} onClick={() => setRows((x) => moveItem(x, i, i + 1))}><IconArrowDown size={14} /></ActionIcon>
                  <ActionIcon size="sm" variant="subtle" color="red" onClick={() => setRows((x) => x.filter((_, j) => j !== i))}><IconTrash size={14} /></ActionIcon>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} w={140} onClick={() => setRows((r) => [...r, { slug: "", title: "" }])}>Add topic</Button>
    </Stack>
  );
}
