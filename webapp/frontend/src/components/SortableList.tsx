import { DndContext, KeyboardSensor, PointerSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ActionIcon, Group } from "@mantine/core";
import { IconGripVertical, IconX } from "@tabler/icons-react";
import type { ReactNode } from "react";

import { moveItem } from "../lib/sheet";

function Row({ id, children, onRemove }: { id: string; children: ReactNode; onRemove?: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  return (
    <Group ref={setNodeRef} gap={4} wrap="nowrap" py={2}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.6 : 1 }}>
      <ActionIcon size="sm" variant="subtle" color="gray" {...attributes} {...listeners} style={{ cursor: "grab" }} aria-label="drag">
        <IconGripVertical size={14} />
      </ActionIcon>
      <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
      {onRemove && <ActionIcon size="sm" variant="subtle" color="red" onClick={onRemove} aria-label="remove"><IconX size={14} /></ActionIcon>}
    </Group>
  );
}

/** Drag & drop reorderable list (keys must be unique per list: index-suffixed). */
export function SortableList<T>({ items, onChange, render }: {
  items: T[]; onChange: (items: T[]) => void; render: (item: T, i: number) => ReactNode;
}) {
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));
  const ids = items.map((_, i) => `item-${i}`);
  const onDragEnd = (e: DragEndEvent) => {
    if (!e.over || e.active.id === e.over.id) return;
    onChange(moveItem(items, ids.indexOf(String(e.active.id)), ids.indexOf(String(e.over.id))));
  };
  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        {items.map((it, i) => (
          <Row key={ids[i]} id={ids[i]} onRemove={() => onChange(items.filter((_, j) => j !== i))}>{render(it, i)}</Row>
        ))}
      </SortableContext>
    </DndContext>
  );
}
