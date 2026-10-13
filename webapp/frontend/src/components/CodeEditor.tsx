import Editor, { DiffEditor, type OnMount } from "@monaco-editor/react";
import { useComputedColorScheme } from "@mantine/core";
import { useEffect, useRef } from "react";

import { monaco } from "../lib/monaco";

interface Props {
  value: string;
  onChange?: (v: string) => void;
  language: "python" | "latex" | "yaml" | "json" | "plaintext";
  readOnly?: boolean;
  onSave?: () => void;
  height?: string | number;
  revealLine?: number | null;
  wordWrap?: boolean;
}

export function CodeEditor({ value, onChange, language, readOnly, onSave, height = "100%", revealLine, wordWrap }: Props) {
  const scheme = useComputedColorScheme("light");
  const saveRef = useRef(onSave);
  saveRef.current = onSave;
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  const onMount: OnMount = (editor) => {
    editorRef.current = editor;
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => saveRef.current?.());
    if (revealLine) editor.revealLineInCenter(revealLine);
  };

  useEffect(() => {
    if (revealLine && editorRef.current) editorRef.current.revealLineInCenter(revealLine);
  }, [revealLine]);

  return (
    <Editor
      height={height}
      language={language}
      value={value}
      theme={scheme === "dark" ? "vs-dark" : "vs"}
      onChange={(v) => onChange?.(v ?? "")}
      onMount={onMount}
      options={{
        readOnly,
        minimap: { enabled: false },
        fontSize: 13,
        wordWrap: wordWrap || language === "latex" ? "on" : "off",
        scrollBeyondLastLine: false,
        tabSize: language === "yaml" ? 2 : 4,
        automaticLayout: true,
        renderWhitespace: "selection",
      }}
    />
  );
}

export function DiffView({ original, modified, language, height = "100%" }: {
  original: string; modified: string; language: Props["language"]; height?: string | number;
}) {
  const scheme = useComputedColorScheme("light");
  return (
    <DiffEditor
      height={height}
      language={language}
      original={original}
      modified={modified}
      theme={scheme === "dark" ? "vs-dark" : "vs"}
      options={{ readOnly: true, renderSideBySide: true, minimap: { enabled: false }, automaticLayout: true, fontSize: 13 }}
    />
  );
}
