import { Code, Text } from "@mantine/core";

export function UnifiedDiff({ diff }: { diff: string }) {
  if (!diff.trim()) return <Text c="dimmed">No changes.</Text>;
  return (
    <Code block style={{ whiteSpace: "pre", overflowX: "auto", fontSize: 12 }}>
      {diff.split("\n").map((line, i) => {
        const color = line.startsWith("+") && !line.startsWith("+++")
          ? "var(--mantine-color-green-light)"
          : line.startsWith("-") && !line.startsWith("---")
            ? "var(--mantine-color-red-light)"
            : line.startsWith("@@") ? "var(--mantine-color-blue-light)" : undefined;
        return (
          <div key={i} style={{ background: color }}>
            {line || " "}
          </div>
        );
      })}
    </Code>
  );
}
