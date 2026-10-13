import { MultiSelect, Select } from "@mantine/core";
import { useMemo } from "react";

import { useTasks, useTopics } from "../api/hooks";

export function useTopicOptions() {
  const { data } = useTopics();
  return useMemo(
    () => (data ?? []).map((t) => ({ value: t.slug, label: `${"  ".repeat(t.depth)}${t.slug} — ${t.title} (${t.count})` })),
    [data],
  );
}

export function useRefOptions() {
  const { data } = useTasks();
  return useMemo(() => {
    const opts: { value: string; label: string }[] = [];
    for (const t of data?.tasks ?? []) {
      if (t.broken) continue;
      opts.push({ value: t.id, label: `${t.id} — ${t.title} (c=${t.complexity})` });
      for (const p of t.presets) if (p !== "default") opts.push({ value: `${t.id}@${p}`, label: `${t.id}@${p}` });
    }
    return opts;
  }, [data]);
}

export function TopicPicker({ value, onChange, label, placeholder }: {
  value: string[]; onChange: (v: string[]) => void; label?: string; placeholder?: string;
}) {
  const options = useTopicOptions();
  // keep unknown values visible (validation reports them)
  const data = useMemo(() => {
    const known = new Set(options.map((o) => o.value));
    return [...options, ...value.filter((v) => !known.has(v)).map((v) => ({ value: v, label: `${v} (unknown)` }))];
  }, [options, value]);
  return <MultiSelect label={label} placeholder={placeholder} data={data} value={value} onChange={onChange} searchable clearable />;
}

export function TaskRefPicker({ value, onChange, label, placeholder, exclude }: {
  value: string | null; onChange: (v: string | null) => void; label?: string; placeholder?: string; exclude?: string[];
}) {
  const options = useRefOptions();
  const data = useMemo(() => options.filter((o) => !exclude?.includes(o.value)), [options, exclude]);
  return <Select label={label} placeholder={placeholder ?? "add task…"} data={data} value={value} onChange={onChange} searchable clearable limit={200} />;
}

export function TaskRefsPicker({ value, onChange, label }: { value: string[]; onChange: (v: string[]) => void; label?: string }) {
  const options = useRefOptions();
  const data = useMemo(() => {
    const known = new Set(options.map((o) => o.value));
    return [...options, ...value.filter((v) => !known.has(v)).map((v) => ({ value: v, label: `${v} (unknown)` }))];
  }, [options, value]);
  return <MultiSelect label={label} data={data} value={value} onChange={onChange} searchable limit={200} />;
}
