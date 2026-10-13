import { Alert, Badge, Group, NavLink, ScrollArea, Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { get } from "../api/client";
import { useGitStatus } from "../api/hooks";
import { ErrorAlert } from "../components/ErrorAlert";
import { UnifiedDiff } from "../components/UnifiedDiff";
import { shortSha } from "../lib/format";

const LABEL: Record<string, string> = { M: "modified", A: "added", D: "deleted", R: "renamed", "?": "untracked" };

export function GitPage() {
  const { data, error } = useGitStatus();
  const [path, setPath] = useState<string | null>(null);
  const diff = useQuery({
    queryKey: ["diff", path],
    queryFn: () => get<string>(`/git/diff${path ? `?path=${encodeURIComponent(path)}` : ""}`),
  });
  return (
    <Stack gap="sm">
      <Title order={3}>Git</Title>
      <Text size="sm" c="dimmed">Read-only. Commit and push in your own git tool — issued runs record the commit.</Text>
      <ErrorAlert error={error} />
      {data && !data.available && <Alert color="gray">Not a git repository: {data.error}</Alert>}
      {data?.available && (
        <Group gap="xs">
          <Badge variant="light">{data.branch}</Badge>
          <Text size="sm" ff="monospace">{shortSha(data.head)}</Text>
          <Text size="sm">{data.subject}</Text>
          {data.dirty ? <Badge color="orange">uncommitted changes</Badge> : <Badge color="green">clean</Badge>}
        </Group>
      )}
      <Group align="flex-start" wrap="nowrap">
        <ScrollArea w={340} h="calc(100vh - 220px)" style={{ flexShrink: 0 }}>
          <NavLink label="All changes" active={path === null} onClick={() => setPath(null)} />
          {data?.files.map((f) => {
            const code = f.status.trim()[0] ?? "?";
            return (
              <NavLink key={f.path} active={path === f.path} onClick={() => setPath(f.path)}
                label={<Text size="xs" ff="monospace" truncate>{f.path}</Text>}
                leftSection={<Badge size="xs" w={70} variant="light" color={code === "?" ? "gray" : code === "D" ? "red" : "blue"}>{LABEL[code] ?? f.status}</Badge>} />
            );
          })}
        </ScrollArea>
        <ScrollArea style={{ flex: 1 }} h="calc(100vh - 220px)">
          <ErrorAlert error={diff.error} />
          {diff.data !== undefined && <UnifiedDiff diff={diff.data} />}
        </ScrollArea>
      </Group>
    </Stack>
  );
}
