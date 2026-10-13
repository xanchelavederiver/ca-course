import { Alert, Anchor, Badge, Box, Button, Code, Group, Loader, Spoiler, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { get, put } from "../api/client";
import { keys } from "../api/hooks";
import { CodeEditor } from "../components/CodeEditor";
import { ErrorAlert } from "../components/ErrorAlert";
import { useUnsavedGuard } from "../lib/hooks";

interface ModuleInfo {
  path: string;
  source: string;
  import_error: string | null;
  syntax_error: string | null;
  tasks: string[];
}

/** Edit a whole task module by path — the way back when a module does not import. */
export function ModulePage() {
  const [params] = useSearchParams();
  const path = params.get("path") ?? "";
  const qc = useQueryClient();
  const { data, error, isLoading } = useQuery({
    queryKey: ["module", path],
    queryFn: () => get<ModuleInfo>(`/modules?path=${encodeURIComponent(path)}`),
  });
  const [code, setCode] = useState<string | null>(null);
  useEffect(() => setCode(data?.source ?? null), [data?.source]);
  const dirty = code !== null && data !== undefined && code !== data.source;
  useUnsavedGuard(dirty);

  const save = async () => {
    if (code === null) return;
    const r = await put<{ ok: boolean; syntax_error: string | null }>("/modules", { path, source: code });
    notifications.show(r.ok ? { color: "green", message: "Saved; the engine reloads it." } : { color: "orange", message: `Saved with a syntax error: ${r.syntax_error}` });
    // give the engine a moment to restart before re-reading import errors
    setTimeout(() => {
      qc.invalidateQueries({ queryKey: ["module", path] });
      qc.invalidateQueries({ queryKey: keys.tasks });
      qc.invalidateQueries({ queryKey: keys.engine });
    }, 300);
  };

  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error} />;
  return (
    <Stack h="calc(100vh - 80px)" gap="xs">
      <Group justify="space-between">
        <Group gap="xs">
          <Title order={4} ff="monospace">{path}</Title>
          {dirty && <Badge color="orange" variant="light">unsaved</Badge>}
        </Group>
        <Button size="xs" onClick={save} disabled={!dirty}>Save</Button>
      </Group>
      {data.tasks.length > 0 && (
        <Text size="sm">Tasks: {data.tasks.map((t) => <Anchor key={t} component={Link} to={`/tasks/${encodeURIComponent(t)}`} mr="xs" ff="monospace">{t}</Anchor>)}</Text>
      )}
      {data.syntax_error && <Alert color="red" p="xs">Syntax error: {data.syntax_error}</Alert>}
      {data.import_error && (
        <Alert color="red" p="xs" title="Import error">
          <Spoiler maxHeight={60} showLabel="more" hideLabel="less">
            <Code block style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>{data.import_error}</Code>
          </Spoiler>
        </Alert>
      )}
      <Box style={{ flex: 1, minHeight: 0 }}>
        <CodeEditor language="python" value={code ?? ""} onChange={setCode} onSave={save} />
      </Box>
    </Stack>
  );
}
