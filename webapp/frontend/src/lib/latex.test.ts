import { describe, expect, it } from "vitest";

import { segments, textToHtml } from "./latex";

describe("segments", () => {
  it("splits inline and display math", () => {
    expect(segments("Найти $x$: \\[g^x \\equiv h\\] и \\(y\\).")).toEqual([
      { kind: "text", text: "Найти " },
      { kind: "math", tex: "x", display: false },
      { kind: "text", text: ": " },
      { kind: "math", tex: "g^x \\equiv h", display: true },
      { kind: "text", text: " и " },
      { kind: "math", tex: "y", display: false },
      { kind: "text", text: "." },
    ]);
  });

  it("handles escaped dollars and environments", () => {
    expect(segments("цена \\$5 и $a\\$b$")).toEqual([
      { kind: "text", text: "цена \\$5 и " },
      { kind: "math", tex: "a\\$b", display: false },
    ]);
    const s = segments("a \\begin{align*}x&=1\\end{align*} \\begin{tabular}{c}1\\end{tabular}");
    expect(s.map((x) => x.kind)).toEqual(["text", "math", "text", "raw"]);
  });

  it("leaves unbalanced math as text", () => {
    expect(segments("a $b")).toEqual([{ kind: "text", text: "a $b" }]);
  });
});

describe("textToHtml", () => {
  it("converts a small subset", () => {
    expect(textToHtml("\\textbf{Да} --- <x> ~ a\\\\b")).toBe("<b>Да</b> — &lt;x&gt;   a<br>b");
  });
});
