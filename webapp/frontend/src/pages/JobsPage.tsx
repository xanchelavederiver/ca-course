import { Group, NavLink, ScrollArea, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";

import { useJobs } from "../api/hooks";
import { JobLog, StatusBadge } from "../components/JobLog";
import { ago } from "../lib/format";

export function JobsPage() {
  const { data } = useJobs();
  const [sel, setSel] = useState<string | null>(null);
  return (
    <Stack gap="sm">
      <Title order={3}>Jobs</Title>
      <Text size="sm" c="dimmed">Drafts, issues, verifications and validation runs since the server started.</Text>
      <Group align="flex-start" wrap="nowrap">
        <ScrollArea w={380} h="calc(100vh - 180px)" style={{ flexShrink: 0 }}>
          {(data ?? []).map((j) => (
            <NavLink key={j.id} active={sel === j.id} onClick={() => setSel(j.id)} label={j.title}
              description={`${j.kind} · ${ago(j.created)}`} rightSection={<StatusBadge status={j.status} />} />
          ))}
          {data?.length === 0 && <Text c="dimmed" size="sm">No jobs yet.</Text>}
        </ScrollArea>
        <div style={{ flex: 1, minWidth: 0 }}>
          {sel && <JobLog jobId={sel}>{(r) => <pre style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>{JSON.stringify(r, null, 2).slice(0, 20000)}</pre>}</JobLog>}
        </div>
      </Group>
    </Stack>
  );
}
