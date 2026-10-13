// MathJax 3 (bundled) for the instant preview, with macros from ca-common.sty.
import { browserAdaptor } from "mathjax-full/js/adaptors/browserAdaptor.js";
import { RegisterHTMLHandler } from "mathjax-full/js/handlers/html.js";
import { TeX } from "mathjax-full/js/input/tex.js";
import { AllPackages } from "mathjax-full/js/input/tex/AllPackages.js";
import { mathjax } from "mathjax-full/js/mathjax.js";
import { SVG } from "mathjax-full/js/output/svg.js";

type Macros = Record<string, string | [string, number]>;

let doc: ReturnType<typeof mathjax.document> | null = null;
let docMacros: Macros | null = null;

function getDoc(macros: Macros) {
  if (!doc || docMacros !== macros) {
    if (!doc) RegisterHTMLHandler(browserAdaptor());
    const tex = new TeX({
      packages: AllPackages.filter((p: string) => p !== "bussproofs"),
      macros: { textrm: ["\\text{#1}", 1], ...macros },
      formatError: (_jax: unknown, err: Error) => {
        throw err;
      },
    });
    doc = mathjax.document(document, { InputJax: tex, OutputJax: new SVG({ fontCache: "local" }) });
    docMacros = macros;
  }
  return doc;
}

/** Render TeX to an SVG element (throws on TeX errors). */
export function renderMath(tex: string, display: boolean, macros: Macros): HTMLElement {
  return getDoc(macros).convert(tex, { display }) as HTMLElement;
}
