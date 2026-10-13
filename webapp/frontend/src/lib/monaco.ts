// Bundle Monaco locally (no CDN): editor core + the languages we need.
import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import "monaco-editor/esm/vs/editor/edcore.main";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution";
import "monaco-editor/esm/vs/basic-languages/yaml/yaml.contribution";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };

// LaTeX with the taskgen template syntax (\VAR{...}, \BLOCK{...}).
monaco.languages.register({ id: "latex" });
monaco.languages.setMonarchTokensProvider("latex", {
  tokenizer: {
    root: [
      [/\\(VAR|BLOCK)\{/, { token: "keyword.template", next: "@template" }],
      [/%.*$/, "comment"],
      [/\\(begin|end)\{[^}]*\}/, "keyword"],
      [/\\[a-zA-Z@]+\*?/, "tag"],
      [/\\./, "tag"],
      [/\$\$|\$|\\\[|\\\]|\\\(|\\\)/, "string"],
      [/[{}]/, "delimiter.bracket"],
      [/[&^_]/, "operator"],
      [/\d+/, "number"],
    ],
    template: [
      [/\{/, { token: "keyword.template", next: "@push" }],
      [/\}/, { token: "keyword.template", next: "@pop" }],
      [/[^{}]+/, "variable"],
    ],
  },
} as monaco.languages.IMonarchLanguage);
monaco.languages.setLanguageConfiguration("latex", {
  comments: { lineComment: "%" },
  brackets: [["{", "}"], ["[", "]"], ["(", ")"]],
  autoClosingPairs: [{ open: "{", close: "}" }, { open: "[", close: "]" }, { open: "(", close: ")" }, { open: "$", close: "$" }],
});

loader.config({ monaco });

export { monaco };
