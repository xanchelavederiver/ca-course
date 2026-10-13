import { ActionIcon, Anchor, Box, Group, Loader, Select, Text, Tooltip } from "@mantine/core";
import { IconDownload, IconExternalLink, IconZoomIn, IconZoomOut } from "@tabler/icons-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import { fileUrl } from "../api/client";

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

type PdfDoc = Awaited<ReturnType<typeof pdfjs.getDocument>["promise"]>;

export interface OutlineItem {
  title: string;
  page: number;
  depth: number;
}

async function flattenOutline(pdf: PdfDoc): Promise<OutlineItem[]> {
  const outline = await pdf.getOutline();
  const out: OutlineItem[] = [];
  const walk = async (items: typeof outline, depth: number) => {
    for (const it of items ?? []) {
      try {
        const dest = typeof it.dest === "string" ? await pdf.getDestination(it.dest) : it.dest;
        if (dest && dest[0]) out.push({ title: it.title, page: (await pdf.getPageIndex(dest[0])) + 1, depth });
      } catch {
        /* unresolvable destination */
      }
      await walk(it.items, depth + 1);
    }
  };
  await walk(outline, 0);
  return out;
}

/** Lazily rendered page: only pages near the viewport are drawn. */
function LazyPage({ n, width, root }: { n: number; width: number; root: HTMLElement | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(n <= 2);
  useEffect(() => {
    const el = ref.current;
    if (!el || visible) return;
    const io = new IntersectionObserver((es) => es.some((e) => e.isIntersecting) && setVisible(true), {
      root, rootMargin: "800px 0px",
    });
    io.observe(el);
    return () => io.disconnect();
  }, [root, visible]);
  return (
    <div ref={ref} data-page={n} style={{ minHeight: visible ? undefined : width * 1.414, marginBottom: 8 }}>
      {visible && <Page pageNumber={n} width={width} renderAnnotationLayer renderTextLayer />}
    </div>
  );
}

interface ViewerProps {
  path: string;
  version?: string | number;
  height?: string | number;
  title?: string;
}

/** A fresh viewer per file version: pages of a previous document must never
 * render against a newly loaded one (pdf.js destroys the old transport). */
export function PdfViewer(props: ViewerProps) {
  return <Viewer key={fileUrl(props.path, { v: props.version })} {...props} />;
}

function Viewer({ path, version, height = "75vh", title }: ViewerProps) {
  const url = fileUrl(path, { v: version });
  const [pages, setPages] = useState(0);
  const [outline, setOutline] = useState<OutlineItem[]>([]);
  const [zoom, setZoom] = useState(1);
  const scroller = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(Math.max(200, el.clientWidth - 24)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const onLoad = useCallback(async (pdf: PdfDoc) => {
    setPages(pdf.numPages);
    setOutline(await flattenOutline(pdf));
  }, []);

  const jump = (page: number) => {
    const el = scroller.current?.querySelector(`[data-page="${page}"]`);
    el?.scrollIntoView({ block: "start" });
  };

  const jumpData = useMemo(
    () => outline.map((o, i) => ({ value: String(i), label: `${"  ".repeat(o.depth)}${o.title} (p. ${o.page})` })),
    [outline],
  );

  return (
    <Box>
      <Group justify="space-between" mb={4} gap="xs" wrap="nowrap">
        <Text size="sm" fw={500} truncate>{title ?? path.split("/").pop()}</Text>
        <Group gap={4} wrap="nowrap">
          {jumpData.length > 0 && (
            <Select size="xs" placeholder="jump to…" data={jumpData} searchable w={220}
              onChange={(v) => v != null && jump(outline[Number(v)].page)} value={null} />
          )}
          <Text size="xs" c="dimmed">{pages ? `${pages} p.` : ""}</Text>
          <ActionIcon variant="subtle" onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}><IconZoomOut size={16} /></ActionIcon>
          <ActionIcon variant="subtle" onClick={() => setZoom((z) => Math.min(3, z + 0.25))}><IconZoomIn size={16} /></ActionIcon>
          <Tooltip label="open in a new tab">
            <Anchor href={url} target="_blank"><IconExternalLink size={16} /></Anchor>
          </Tooltip>
          <Tooltip label="download">
            <Anchor href={fileUrl(path, { download: true })}><IconDownload size={16} /></Anchor>
          </Tooltip>
        </Group>
      </Group>
      <div ref={scroller} style={{ height, overflow: "auto", background: "var(--mantine-color-gray-light)", padding: 12 }} data-testid="pdf-viewer">
        <Document file={url} onLoadSuccess={onLoad} loading={<Loader size="sm" />}
          error={<Text c="red" size="sm">Could not load {path}</Text>}>
          {Array.from({ length: pages }, (_, i) => (
            <LazyPage key={i} n={i + 1} width={width * zoom} root={scroller.current} />
          ))}
        </Document>
      </div>
    </Box>
  );
}
