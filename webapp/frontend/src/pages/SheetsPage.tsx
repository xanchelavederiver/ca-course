import { Anchor, Badge, Button, Group, Modal, NumberInput, SegmentedControl, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { post } from "../api/client";
import { keys, useSheets } from "../api/hooks";
import { ErrorAlert } from "../components/ErrorAlert";
import { ago } from "../lib/format";

export function KindBadge({ kind }: { kind: string | null }) {
  return <Badge size="sm" variant="light" color={kind === "individual" ? "grape" : "teal"}>{kind ?? "?"}</Badge>;
}

export function SheetsPage() {
  const { data, error } = useSheets();
  const [opened, ctl] = useDisclosure(false);
  const groups = useMemo(() => {
    const m = new Map<string, NonNullable<typeof data>>();
    for (const s of data ?? []) m.set(s.dir, [...(m.get(s.dir) ?? []), s]);
    return [...m.entries()];
  }, [data]);

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Sheets</Title>
        <Button size="xs" leftSection={<IconPlus size={14} />} onClick={ctl.open}>New sheet</Button>
      </Group>
      <ErrorAlert error={error} />
      {groups.map(([dir, sheets]) => (
        <div key={dir}>
          <Text fw={600} mb={4}>{dir}</Text>
          <Table striped highlightOnHover fz="sm" verticalSpacing={4}>
            <Table.Thead>
              <Table.Tr><Table.Th>title</Table.Th><Table.Th>id</Table.Th><Table.Th>kind</Table.Th><Table.Th>variants</Table.Th>
                <Table.Th>last draft</Table.Th><Table.Th>last issue</Table.Th></Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sheets.map((s) => (
                <Table.Tr key={s.path}>
                  <Table.Td><Anchor component={Link} to={`/${s.path}`}>{s.title ?? s.path}</Anchor>
                    {s.error && <Text size="xs" c="red">{s.error}</Text>}</Table.Td>
                  <Table.Td ff="monospace">{s.id}</Table.Td>
                  <Table.Td><KindBadge kind={s.kind} /></Table.Td>
                  <Table.Td>{s.variants}</Table.Td>
                  <Table.Td>{ago(s.last_draft)}</Table.Td>
                  <Table.Td>{s.last_issue ? (
                    <Anchor component={Link} to={`/archive/${s.id}/${s.last_issue.run}`}>{s.last_issue.run}</Anchor>
                  ) : "—"}{s.issued_runs > 1 && <Text span size="xs" c="dimmed"> (+{s.issued_runs - 1})</Text>}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      ))}
      <NewSheetModal opened={opened} onClose={ctl.close} dirs={groups.map(([d]) => d)} />
    </Stack>
  );
}

function NewSheetModal({ opened, onClose, dirs }: { opened: boolean; onClose: () => void; dirs: string[] }) {
  const [dir, setDir] = useState("sem1");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"classroom" | "individual">("classroom");
  const [title, setTitle] = useState("");
  const [semester, setSemester] = useState<number | null>(1);
  const [err, setErr] = useState<unknown>(null);
  const nav = useNavigate();
  const qc = useQueryClient();
  const file = name.toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, "");
  const id = `${dir.replace(/[^a-z0-9]+/g, "")}-${file}`;
  const path = `sheets/${dir}/${file}.yaml`;

  const create = async () => {
    setErr(null);
    try {
      await post("/sheets", { path, kind, id, title, semester });
      qc.invalidateQueries({ queryKey: keys.sheets });
      onClose();
      nav(`/${path}`);
    } catch (e) {
      setErr(e);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="New sheet">
      <Stack gap="sm">
        <SegmentedControl value={kind} onChange={(v) => setKind(v as typeof kind)}
          data={[{ value: "classroom", label: "Classroom (one sheet)" }, { value: "individual", label: "Individual (variants)" }]} />
        <TextInput label="Directory" description={`existing: ${dirs.join(", ")}`} value={dir} onChange={(e) => setDir(e.currentTarget.value)} />
        <TextInput label="File name" placeholder="seminar-03" value={name} onChange={(e) => setName(e.currentTarget.value)} />
        <TextInput label="Title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
        <NumberInput label="Semester" value={semester ?? ""} onChange={(v) => setSemester(v === "" ? null : Number(v))} min={1} max={2} />
        <Text size="xs" c="dimmed">{path} · id <code>{id}</code></Text>
        <ErrorAlert error={err} />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>Cancel</Button>
          <Button onClick={create} disabled={!file || !title}>Create</Button>
        </Group>
      </Stack>
    </Modal>
  );
}
