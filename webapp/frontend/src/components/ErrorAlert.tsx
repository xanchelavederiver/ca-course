import { Alert, Code, List, Spoiler } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";

import { ApiError } from "../api/client";

export function ErrorAlert({ error, title }: { error: unknown; title?: string }) {
  if (!error) return null;
  const e = error as Error;
  const api = error instanceof ApiError ? error : null;
  const traceback = api?.traceback ?? (error as { traceback?: string }).traceback ?? null;
  const log = api?.body?.log as string | undefined;
  return (
    <Alert color="red" icon={<IconAlertTriangle size={18} />} title={title ?? e.message} variant="light">
      {title && <div>{e.message}</div>}
      {api && api.problems.length > 0 && (
        <List size="sm" mt={4}>
          {api.problems.map((p, i) => <List.Item key={i}>{p}</List.Item>)}
        </List>
      )}
      {(traceback || log) && (
        <Spoiler maxHeight={0} showLabel="details" hideLabel="hide" mt={4}>
          <Code block style={{ whiteSpace: "pre-wrap", fontSize: 11 }}>{traceback ?? log}</Code>
        </Spoiler>
      )}
    </Alert>
  );
}
