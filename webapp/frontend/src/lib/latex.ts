// Split generated LaTeX snippets into text and math for the MathJax quick
// preview. This is deliberately approximate: tables, custom environments and
// layout commands are shown as source; the PDF is the canonical preview.

export type Segment =
  | { kind: "text"; text: string }
  | { kind: "math"; tex: string; display: boolean }
  | { kind: "raw"; text: string };

const DISPLAY_ENVS = ["equation", "equation*", "align", "align*", "gather", "gather*", "multline", "multline*"];
const RAW_ENVS = ["tabular", "longtable", "verbatim", "lstlisting", "tikzpicture"];

function findClose(s: string, from: number, close: string): number {
  // first occurrence of `close` at or after `from`, skipping escaped characters (\$, \\)
  for (let i = from; i < s.length; i++) {
    if (s.startsWith(close, i)) return i;
    if (s[i] === "\\") i++;
  }
  return -1;
}

export function segments(src: string): Segment[] {
  const out: Segment[] = [];
  let text = "";
  const flush = () => {
    if (text) out.push({ kind: "text", text });
    text = "";
  };
  let i = 0;
  while (i < src.length) {
    const rest = src.slice(i);
    let m: RegExpMatchArray | null;
    if (rest.startsWith("\\[") || rest.startsWith("$$")) {
      const close = rest.startsWith("\\[") ? "\\]" : "$$";
      const end = findClose(src, i + 2, close);
      if (end >= 0) {
        flush();
        out.push({ kind: "math", tex: src.slice(i + 2, end), display: true });
        i = end + 2;
        continue;
      }
    } else if (rest.startsWith("\\(")) {
      const end = findClose(src, i + 2, "\\)");
      if (end >= 0) {
        flush();
        out.push({ kind: "math", tex: src.slice(i + 2, end), display: false });
        i = end + 2;
        continue;
      }
    } else if (rest[0] === "$") {
      const end = findClose(src, i + 1, "$");
      if (end >= 0) {
        flush();
        out.push({ kind: "math", tex: src.slice(i + 1, end), display: false });
        i = end + 1;
        continue;
      }
    } else if ((m = rest.match(/^\\begin\{([a-zA-Z*]+)\}/))) {
      const env = m[1];
      const endTag = `\\end{${env}}`;
      const end = src.indexOf(endTag, i + m[0].length);
      if (end >= 0 && (DISPLAY_ENVS.includes(env) || RAW_ENVS.includes(env))) {
        flush();
        const whole = src.slice(i, end + endTag.length);
        out.push(DISPLAY_ENVS.includes(env) ? { kind: "math", tex: whole, display: true } : { kind: "raw", text: whole });
        i = end + endTag.length;
        continue;
      }
    } else if (rest[0] === "\\" && rest.length > 1 && "$%&#_{}".includes(rest[1])) {
      text += rest.slice(0, 2);
      i += 2;
      continue;
    }
    text += src[i];
    i++;
  }
  flush();
  return out;
}

const TEXT_CMDS: [RegExp, string][] = [
  [/\\textbf\{([^{}]*)\}/g, "<b>$1</b>"],
  [/\\(?:emph|textit)\{([^{}]*)\}/g, "<i>$1</i>"],
  [/\\texttt\{([^{}]*)\}/g, "<code>$1</code>"],
  [/\\underline\{([^{}]*)\}/g, "<u>$1</u>"],
];

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Text-mode LaTeX -> small HTML subset (bold/italic, lists, paragraphs, dashes). */
export function textToHtml(s: string): string {
  let h = escapeHtml(s);
  h = h.replace(/(^|[^\\])%[^\n]*/g, "$1");
  for (const [re, rep] of TEXT_CMDS) h = h.replace(re, rep);
  h = h
    .replace(/\\(?:begin|end)\{(?:itemize|enumerate)\}/g, "")
    .replace(/\\item\s*/g, "<br>• ")
    .replace(/\\\\(\[[^\]]*\])?/g, "<br>")
    .replace(/\n\s*\n/g, "<br><br>")
    .replace(/\\(?:par|medskip|smallskip|bigskip|noindent|clearpage|newline)\b/g, "<br>")
    .replace(/---/g, "—")
    .replace(/--/g, "–")
    .replace(/~/g, " ")
    .replace(/\\([$%&#_{}])/g, "$1")
    .replace(/\\,/g, " ");
  return h;
}
