import { Accordion, Badge, Card, Code, Group, Text } from "@mantine/core";

import type { Instance } from "../api/types";
import { json } from "../lib/format";
import { MathText } from "./MathText";

export function InstanceCard({ inst, index }: { inst: Instance; index?: number }) {
  return (
    <Card withBorder padding="sm" data-testid="instance">
      <Group gap="xs" mb={6}>
        {index !== undefined && <Badge variant="light">#{index + 1}</Badge>}
        <Text size="xs" c="dimmed" ff="monospace">{inst.task_id}{inst.preset !== "default" ? `@${inst.preset}` : ""} · seed {inst.seed}</Text>
      </Group>
      <MathText tex={inst.statement} />
      <Accordion multiple variant="contained" mt="xs" chevronPosition="left" styles={{ label: { padding: "4px 0" } }}>
        <Accordion.Item value="solution">
          <Accordion.Control><Text size="sm">Solution</Text></Accordion.Control>
          <Accordion.Panel><MathText tex={inst.solution} /></Accordion.Panel>
        </Accordion.Item>
        <Accordion.Item value="answer">
          <Accordion.Control><Text size="sm">Answer &amp; params</Text></Accordion.Control>
          <Accordion.Panel>
            <Text size="xs" fw={600}>answer</Text>
            <Code block>{json(inst.answer)}</Code>
            <Text size="xs" fw={600} mt={4}>params</Text>
            <Code block style={{ maxHeight: 300, overflow: "auto" }}>{json(inst.params)}</Code>
          </Accordion.Panel>
        </Accordion.Item>
        <Accordion.Item value="latex">
          <Accordion.Control><Text size="sm">LaTeX</Text></Accordion.Control>
          <Accordion.Panel>
            <Code block style={{ whiteSpace: "pre-wrap", fontSize: 11 }}>{inst.statement}</Code>
            <Code block mt={4} style={{ whiteSpace: "pre-wrap", fontSize: 11 }}>{inst.solution}</Code>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Card>
  );
}
