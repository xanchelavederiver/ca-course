import {
  ActionIcon, Badge, Button, Card, Chip, Divider, Group, NumberInput, SegmentedControl, Select, SimpleGrid, Stack, Switch,
  Text, TextInput, Textarea,
} from "@mantine/core";
import { IconArrowDown, IconArrowUp, IconPlus, IconTrash } from "@tabler/icons-react";

import { useTasks } from "../api/hooks";
import { emptyGroup, emptySlot, moveItem, parseStudents, splitRef, variantCount, type SheetForm as Form } from "../lib/sheet";
import { TaskRefPicker, TaskRefsPicker, TopicPicker } from "./Pickers";
import { SortableList } from "./SortableList";

const FONT_SIZES = ["10pt", "11pt", "12pt", "14pt", "17pt", "20pt"];

function MoveButtons({ i, n, onMove, onRemove }: { i: number; n: number; onMove: (to: number) => void; onRemove: () => void }) {
  return (
    <Group gap={2}>
      <ActionIcon size="sm" variant="subtle" disabled={i === 0} onClick={() => onMove(i - 1)}><IconArrowUp size={14} /></ActionIcon>
      <ActionIcon size="sm" variant="subtle" disabled={i === n - 1} onClick={() => onMove(i + 1)}><IconArrowDown size={14} /></ActionIcon>
      <ActionIcon size="sm" variant="subtle" color="red" onClick={onRemove}><IconTrash size={14} /></ActionIcon>
    </Group>
  );
}

function RefLabel({ value }: { value: string }) {
  const { data } = useTasks();
  const { id, preset } = splitRef(value);
  const t = data?.tasks.find((x) => x.id === id);
  return (
    <Group gap={6} wrap="nowrap">
      <Text size="sm" ff="monospace">{id}</Text>
      {preset && <Badge size="xs" variant="light">{preset}</Badge>}
      {t ? <Text size="xs" c="dimmed" truncate>{t.title} · c={t.complexity}</Text>
        : data && <Text size="xs" c="red">unknown task</Text>}
    </Group>
  );
}

export function SheetFormView({ form, onChange }: { form: Form; onChange: (f: Form) => void }) {
  const set = <K extends keyof Form>(k: K, v: Form[K]) => onChange({ ...form, [k]: v });
  const doc = form.document ?? {};

  return (
    <Stack gap="sm">
      <SimpleGrid cols={2}>
        <TextInput label="Title" value={form.title} onChange={(e) => set("title", e.currentTarget.value)} />
        <TextInput label="Sheet id" description="archive/<id>/ — keep stable" value={form.id} onChange={(e) => set("id", e.currentTarget.value)} />
        <NumberInput label="Semester" value={form.semester ?? ""} min={1} max={2} onChange={(v) => set("semester", v === "" ? null : Number(v))} />
        <TextInput label="Default preset" description='e.g. "sem2" (used by tasks that have it)' value={form.preset ?? ""}
          onChange={(e) => set("preset", e.currentTarget.value || null)} />
      </SimpleGrid>
      <Textarea label="Intro (LaTeX)" autosize minRows={2} maxRows={12} value={form.intro}
        onChange={(e) => set("intro", e.currentTarget.value)} styles={{ input: { fontFamily: "monospace", fontSize: 12 } }} />
      <Group gap="md" align="flex-end">
        <Select label="Font size" data={FONT_SIZES} value={doc.font_size ?? "14pt"} w={100}
          onChange={(v) => set("document", { ...doc, font_size: v ?? "14pt" })} />
        <Switch label="Table of contents" checked={doc.toc ?? true} onChange={(e) => set("document", { ...doc, toc: e.currentTarget.checked })} />
        <TextInput label="Solutions title suffix" value={doc.solutions_suffix ?? "Решения"} w={180}
          onChange={(e) => set("document", { ...doc, solutions_suffix: e.currentTarget.value })} />
        <TextInput label="Template" placeholder="(default)" value={form.template ?? ""} w={200}
          onChange={(e) => set("template", e.currentTarget.value || null)} />
      </Group>
      <Divider />
      {form.kind === "classroom" ? <Sections form={form} onChange={onChange} /> : <Individual form={form} onChange={onChange} />}
    </Stack>
  );
}

function Sections({ form, onChange }: { form: Form; onChange: (f: Form) => void }) {
  const setSections = (s: Form["sections"]) => onChange({ ...form, sections: s });
  return (
    <Stack gap="sm">
      <Text fw={600}>Sections</Text>
      {form.sections.map((sec, i) => (
        <Card key={i} withBorder padding="sm">
          <Group justify="space-between" mb={4}>
            <TextInput size="xs" label="Section title" value={sec.title} style={{ flex: 1 }}
              onChange={(e) => setSections(form.sections.map((s, j) => (j === i ? { ...s, title: e.currentTarget.value } : s)))} />
            <MoveButtons i={i} n={form.sections.length} onMove={(to) => setSections(moveItem(form.sections, i, to))}
              onRemove={() => setSections(form.sections.filter((_, j) => j !== i))} />
          </Group>
          <Textarea size="xs" label="Intro" autosize minRows={1} value={sec.intro ?? ""}
            onChange={(e) => setSections(form.sections.map((s, j) => (j === i ? { ...s, intro: e.currentTarget.value || null } : s)))} />
          <Text size="xs" fw={500} mt="xs">Tasks (drag to reorder)</Text>
          <SortableList items={sec.tasks} onChange={(tasks) => setSections(form.sections.map((s, j) => (j === i ? { ...s, tasks } : s)))}
            render={(ref) => <RefLabel value={ref} />} />
          <TaskRefPicker value={null} onChange={(v) => v && setSections(form.sections.map((s, j) => (j === i ? { ...s, tasks: [...s.tasks, v] } : s)))} />
        </Card>
      ))}
      <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} w={160}
        onClick={() => setSections([...form.sections, { title: "Раздел", intro: null, tasks: [] }])}>Add section</Button>
    </Stack>
  );
}

function Individual({ form, onChange }: { form: Form; onChange: (f: Form) => void }) {
  const setGroups = (g: Form["groups"]) => onChange({ ...form, groups: g });
  const setSlots = (s: Form["slots"]) => onChange({ ...form, slots: s });
  const b = form.budget;
  return (
    <Stack gap="sm">
      <Group justify="space-between">
        <Text fw={600}>Groups</Text>
        <Text size="sm" c="dimmed">{variantCount(form)} variant(s) in total</Text>
      </Group>
      {form.groups.map((g, i) => (
        <Card key={i} withBorder padding="xs">
          <Group align="flex-start" gap="sm">
            <TextInput size="xs" label="Group" value={g.name} w={120}
              onChange={(e) => setGroups(form.groups.map((x, j) => (j === i ? { ...x, name: e.currentTarget.value } : x)))} />
            <div>
              <Text size="xs" fw={500}>Variants</Text>
              <SegmentedControl size="xs" value={g.mode} data={[{ value: "count", label: "count" }, { value: "students", label: "student list" }]}
                onChange={(v) => setGroups(form.groups.map((x, j) => (j === i ? { ...x, mode: v as "count" | "students" } : x)))} />
            </div>
            {g.mode === "count" ? (
              <NumberInput size="xs" label="Count" min={1} value={g.count} w={90}
                onChange={(v) => setGroups(form.groups.map((x, j) => (j === i ? { ...x, count: Number(v) || 1 } : x)))} />
            ) : (
              <Textarea key={g.students.join("|")} size="xs" label={`Students (${g.students.length}) — paste one per line`} autosize minRows={2} maxRows={10} style={{ flex: 1 }}
                defaultValue={g.students.join("\n")}
                onBlur={(e) => setGroups(form.groups.map((x, j) => (j === i ? { ...x, students: parseStudents(e.currentTarget.value) } : x)))} />
            )}
            <div style={{ marginLeft: "auto" }}>
              <MoveButtons i={i} n={form.groups.length} onMove={(to) => setGroups(moveItem(form.groups, i, to))}
                onRemove={() => setGroups(form.groups.filter((_, j) => j !== i))} />
            </div>
          </Group>
        </Card>
      ))}
      <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} w={140}
        onClick={() => setGroups([...form.groups, emptyGroup(form.groups.length + 1)])}>Add group</Button>

      <Divider />
      <Group gap="lg" align="flex-end">
        <div>
          <Text size="sm" fw={500}>Complexity budget (sum over slots)</Text>
          <SegmentedControl size="xs" value={b.mode} data={["none", "exact", "range"]}
            onChange={(v) => onChange({ ...form, budget: v === "none" ? { mode: "none" } : v === "exact" ? { mode: "exact", value: b.mode === "exact" ? b.value : 8 } : { mode: "range", min: null, max: null } })} />
        </div>
        {b.mode === "exact" && <NumberInput size="xs" label="total" value={b.value} min={0} w={90} onChange={(v) => onChange({ ...form, budget: { mode: "exact", value: Number(v) || 0 } })} />}
        {b.mode === "range" && (
          <>
            <NumberInput size="xs" label="min" value={b.min ?? ""} w={90} onChange={(v) => onChange({ ...form, budget: { ...b, min: v === "" ? null : Number(v) } })} />
            <NumberInput size="xs" label="max" value={b.max ?? ""} w={90} onChange={(v) => onChange({ ...form, budget: { ...b, max: v === "" ? null : Number(v) } })} />
          </>
        )}
        <Switch label="Distinct families (no two tasks of one family in a variant)" checked={form.distinct_families}
          onChange={(e) => onChange({ ...form, distinct_families: e.currentTarget.checked })} />
      </Group>

      <Text fw={600}>Slots</Text>
      {form.slots.map((s, i) => (
        <Card key={i} withBorder padding="xs">
          <Group justify="space-between" align="flex-end" mb={4}>
            <Group gap="xs" align="flex-end">
              <Badge variant="light">{i + 1}</Badge>
              <TextInput size="xs" label="Title" value={s.title ?? ""} w={300}
                onChange={(e) => setSlots(form.slots.map((x, j) => (j === i ? { ...x, title: e.currentTarget.value || null } : x)))} />
              <SegmentedControl size="xs" value={s.source} data={[{ value: "tasks", label: "task list" }, { value: "topics", label: "by topics" }]}
                onChange={(v) => setSlots(form.slots.map((x, j) => (j === i ? { ...x, source: v as "tasks" | "topics" } : x)))} />
            </Group>
            <MoveButtons i={i} n={form.slots.length} onMove={(to) => setSlots(moveItem(form.slots, i, to))}
              onRemove={() => setSlots(form.slots.filter((_, j) => j !== i))} />
          </Group>
          {s.source === "tasks" ? (
            <TaskRefsPicker value={s.tasks} onChange={(v) => setSlots(form.slots.map((x, j) => (j === i ? { ...x, tasks: v } : x)))} />
          ) : (
            <TopicPicker value={s.topics} onChange={(v) => setSlots(form.slots.map((x, j) => (j === i ? { ...x, topics: v } : x)))} />
          )}
          <Group gap="xs" mt={4}>
            <Text size="xs" c="dimmed">complexity filter</Text>
            <Chip.Group multiple value={(s.complexity ?? []).map(String)}
              onChange={(v) => setSlots(form.slots.map((x, j) => (j === i ? { ...x, complexity: v.length ? v.map(Number).sort() : null } : x)))}>
              {["1", "2", "3"].map((c) => <Chip key={c} value={c} size="xs">{c}</Chip>)}
            </Chip.Group>
          </Group>
        </Card>
      ))}
      <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} w={140}
        onClick={() => setSlots([...form.slots, emptySlot()])}>Add slot</Button>
    </Stack>
  );
}
