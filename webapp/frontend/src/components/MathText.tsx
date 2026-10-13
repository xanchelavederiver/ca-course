import { Code, Text } from "@mantine/core";
import { memo, useEffect, useRef } from "react";

import { useMacros } from "../api/hooks";
import { segments, textToHtml } from "../lib/latex";
import { renderMath } from "../lib/mathjax";

function MathSpan({ tex, display, macros }: { tex: string; display: boolean; macros: Record<string, string | [string, number]> }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.replaceChildren();
    try {
      el.appendChild(renderMath(tex, display, macros));
      el.removeAttribute("title");
      el.style.color = "";
    } catch (err) {
      el.textContent = display ? `\\[${tex}\\]` : `$${tex}$`;
      el.title = (err as Error).message;
      el.style.color = "var(--mantine-color-red-7)";
    }
  }, [tex, display, macros]);
  return <span ref={ref} style={display ? { display: "block", textAlign: "center", margin: "6px 0", overflowX: "auto" } : undefined} />;
}

/** Approximate rendering of a LaTeX snippet (text + MathJax); the PDF is canonical. */
export const MathText = memo(function MathText({ tex }: { tex: string }) {
  const { data: macros } = useMacros();
  if (!macros) return <Text size="sm" c="dimmed">…</Text>;
  return (
    <div style={{ lineHeight: 1.6 }}>
      {segments(tex).map((s, i) =>
        s.kind === "math" ? (
          <MathSpan key={i} tex={s.tex} display={s.display} macros={macros} />
        ) : s.kind === "raw" ? (
          <Code key={i} block style={{ fontSize: 11 }}>{s.text}</Code>
        ) : (
          <span key={i} dangerouslySetInnerHTML={{ __html: textToHtml(s.text) }} />
        ),
      )}
    </div>
  );
});
