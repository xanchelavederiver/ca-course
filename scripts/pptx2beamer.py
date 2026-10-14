#!/usr/bin/env python3
"""Convert a PPTX deck into a ca-slides (Beamer) skeleton.

    docker compose run --rm --entrypoint sage taskgen -python scripts/pptx2beamer.py \\
        "tmp/лекции/Lecture 2. ....pptx" materials/sem1/lectures/02-big-integer-arithmetic \\
        [--lecture 2] [--title "..."] [--out slides-skeleton.tex]

Every slide becomes a ``canvasframe`` with

* the title placeholder as the frame title;
* body paragraphs as nested ``itemize`` (by bullet level);
* native PowerPoint equations (OMML) translated to LaTeX math;
* pictures extracted to ``<lecture dir>/img/`` and included with ``\\includegraphics``;
* free text boxes (callouts such as «почему?») as ``\\aside{...}``;
* speaker notes as ``% note:`` comments;
* ``% TODO`` markers where something could not be translated (pictures of
  formulas or handwriting, unknown OMML elements).

The result is a skeleton for a manual pass: fix layout, retype pictures of
formulas, add ``\\penspace``/``\\proofarea`` where proofs were written live.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

from pptx import Presentation
from pptx.parts.image import Image

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "a14": "http://schemas.microsoft.com/office/drawing/2010/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
M = "{%s}" % NS["m"]
A = "{%s}" % NS["a"]
MC = "{%s}" % NS["mc"]

# --- text ----------------------------------------------------------------------------

TEXT_ESC = {"\\": r"\textbackslash{}", "#": r"\#", "$": r"\$", "%": r"\%", "&": r"\&",
            "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
            "–": "--", "—": "---", "…": r"\ldots{}", "\u00a0": "~", "“": "``", "”": "''",
            "\u2009": r"\,", "\t": " "}

# Unicode symbols that may appear in text runs or in math runs
SYMBOLS = {
    "⋅": r"\cdot ", "·": r"\cdot ", "×": r"\times ", "≤": r"\le ", "≥": r"\ge ", "≠": r"\ne ",
    "≡": r"\equiv ", "≈": r"\approx ", "∼": r"\sim ", "→": r"\to ", "←": r"\gets ",
    "⇒": r"\Rightarrow ", "⇔": r"\Leftrightarrow ", "∈": r"\in ", "∉": r"\notin ",
    "⊂": r"\subset ", "⊆": r"\subseteq ", "∪": r"\cup ", "∩": r"\cap ", "∞": r"\infty ",
    "∀": r"\forall ", "∃": r"\exists ", "∣": r"\mid ", "∤": r"\nmid ", "±": r"\pm ", "∓": r"\mp ",
    "−": "-", "∗": "*", "′": "'", "…": r"\ldots ", "⋯": r"\cdots ", "⌊": r"\lfloor ",
    "⌋": r"\rfloor ", "⌈": r"\lceil ", "⌉": r"\rceil ", "‖": r"\| ", "∘": r"\circ ",
    "ℤ": r"\ZZ ", "ℕ": r"\NN ", "ℚ": r"\QQ ", "ℝ": r"\RR ", "ℂ": r"\CC ", "𝔽": r"\FF ",
    "α": r"\alpha ", "β": r"\beta ", "γ": r"\gamma ", "δ": r"\delta ", "ε": r"\varepsilon ", "ϵ": r"\epsilon ",
    "ζ": r"\zeta ", "η": r"\eta ", "θ": r"\theta ", "λ": r"\lambda ", "μ": r"\mu ", "ν": r"\nu ",
    "ξ": r"\xi ", "π": r"\pi ", "ρ": r"\rho ", "σ": r"\sigma ", "τ": r"\tau ", "φ": r"\varphi ",
    "ϕ": r"\phi ", "χ": r"\chi ", "ψ": r"\psi ", "ω": r"\omega ", "Γ": r"\Gamma ", "Δ": r"\Delta ",
    "Θ": r"\Theta ", "Λ": r"\Lambda ", "Π": r"\Pi ", "Σ": r"\Sigma ", "Φ": r"\Phi ", "Ψ": r"\Psi ",
    "Ω": r"\Omega ", "∂": r"\partial ", "∇": r"\nabla ", "√": r"\surd ", "∑": r"\sum ",
    "∏": r"\prod ", "∫": r"\int ", "⟨": r"\langle ", "⟩": r"\rangle ", "∅": r"\emptyset ",
    "¬": r"\neg ", "∧": r"\wedge ", "∨": r"\vee ", "⊕": r"\oplus ", "⊗": r"\otimes ",
    "ℒ": r"\mathcal{L}", "∙": r"\cdot ", "∘": r"\circ ", "≪": r"\ll ", "≫": r"\gg ", "≔": r"\coloneqq ", "∝": r"\propto ", "ℓ": r"\ell ",
}


GREEK = {"ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "ETA", "THETA", "IOTA", "KAPPA",
         "LAMDA", "MU", "NU", "XI", "OMICRON", "PI", "RHO", "SIGMA", "TAU", "UPSILON", "PHI", "CHI",
         "PSI", "OMEGA"}


def demath_char(ch: str) -> str:
    """Mathematical alphanumeric symbols (U+1D400..): italic/bold letters, digits and
    Greek -> ASCII letters/digits or the plain Greek letter."""
    if not 0x1D400 <= ord(ch) <= 0x1D7FF:
        return {"ℎ": "h"}.get(ch, ch)
    name = unicodedata.name(ch, "")
    words = name.split()
    if "DIGIT" in words:
        return str(["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT",
                    "NINE"].index(words[-1]))
    if words and words[-1] == "SYMBOL" and len(words) >= 2 and words[-2] in GREEK:
        words = words[:-1]   # EPSILON SYMBOL etc. -> plain letter
    letter = words[-1] if words else ""
    if letter in GREEK:
        return unicodedata.lookup("GREEK %s LETTER %s" % ("CAPITAL" if "CAPITAL" in words else "SMALL",
                                                          letter))
    if len(letter) == 1:
        return letter if "CAPITAL" in words else letter.lower()
    return ch


def esc_text(s: str) -> str:
    out = []
    for ch in s:
        ch = demath_char(ch)
        if ch in TEXT_ESC:
            out.append(TEXT_ESC[ch])
        elif ch in SYMBOLS and ch not in "−":
            out.append(f"${SYMBOLS[ch].strip()}$")
        else:
            out.append(ch)
    return "".join(out)


def is_cyrillic(s: str) -> bool:
    return bool(re.search("[А-Яа-яЁё]", s))


# --- OMML -> LaTeX ---------------------------------------------------------------------

NARY = {"∑": r"\sum", "∏": r"\prod", "∫": r"\int", "∬": r"\iint", "∮": r"\oint", "⋃": r"\bigcup",
        "⋂": r"\bigcap", "⨁": r"\bigoplus", "⨂": r"\bigotimes", "∐": r"\coprod"}
ACCENT = {"\u0302": r"\hat", "^": r"\hat", "\u0303": r"\tilde", "~": r"\tilde", "\u0304": r"\bar",
          "\u0305": r"\overline", "\u20d7": r"\vec", "\u0307": r"\dot", "\u0308": r"\ddot",
          "\u030c": r"\check", "\u0306": r"\breve"}
DELIM = {"(": "(", ")": ")", "[": "[", "]": "]", "{": r"\{", "}": r"\}", "|": "|", "‖": r"\|",
         "⌊": r"\lfloor", "⌋": r"\rfloor", "⌈": r"\lceil", "⌉": r"\rceil", "⟨": r"\langle",
         "⟩": r"\rangle", "": "."}
FUNCS = {"sin", "cos", "tan", "log", "ln", "lg", "exp", "min", "max", "gcd", "lim", "deg", "det",
         "sup", "inf", "mod", "arg", "ker", "dim"}


class Omml:
    def __init__(self) -> None:
        self.todo: list[str] = []

    def val(self, el, path: str, attr: str = "val", default: str | None = None) -> str | None:
        node = el.find(path, NS) if el is not None else None
        if node is None:
            return default
        return node.get(M + attr, default)

    def kids(self, el) -> str:
        return "".join(self.conv(c) for c in el) if el is not None else ""

    def arg(self, el, name: str) -> str:
        return self.kids(el.find(f"m:{name}", NS))

    def run(self, r) -> str:
        text = "".join(t.text or "" for t in r.findall("m:t", NS))
        sty = self.val(r, "m:rPr/m:sty")
        nor = r.find("m:rPr/m:nor", NS) is not None
        if is_cyrillic(text) or (nor and re.search(r"[A-Za-z]{2,}", text)):
            return r"\text{" + esc_text(text) + "}"
        out = []
        word = "".join(demath_char(c) for c in text)
        if word in FUNCS:
            return "\\" + word + " "
        if sty == "p" and re.fullmatch(r"[A-Za-z]{2,}", word):
            return r"\mathrm{" + word + "}"
        for ch in text:
            ch = demath_char(ch)
            if ch in SYMBOLS:
                out.append(SYMBOLS[ch])
            elif ch in "{}":
                out.append("\\" + ch)
            elif ch in "#%&_$":
                out.append("\\" + ch)
            elif ch in "\u00a0\t":
                out.append("~")
            else:
                out.append(ch)
        return "".join(out)

    def conv(self, el) -> str:
        tag = el.tag.replace(M, "") if el.tag.startswith(M) else None
        if tag is None:
            return ""
        if tag in ("rPr", "ctrlPr", "fPr", "sSupPr", "sSubPr", "sSubSupPr", "dPr", "naryPr",
                   "radPr", "accPr", "barPr", "funcPr", "limLowPr", "limUppPr", "eqArrPr", "mPr",
                   "mrPr", "boxPr", "borderBoxPr", "groupChrPr", "phantPr", "sPrePr", "oMathParaPr",
                   "argPr"):
            return ""
        if tag == "r":
            return self.run(el)
        if tag in ("oMath", "e", "num", "den", "sub", "sup", "deg", "lim", "fName", "box", "borderBox",
                   "phant"):
            return self.kids(el)
        if tag == "oMathPara":
            rows = [self.conv(c) for c in el.findall("m:oMath", NS)]
            return r" \\ ".join(r for r in rows if r.strip())
        if tag == "f":
            num, den = self.arg(el, "num"), self.arg(el, "den")
            typ = self.val(el, "m:fPr/m:type")
            if typ == "lin":
                return f"{num}/{den}"
            if typ == "noBar":
                return rf"\genfrac{{}}{{}}{{0pt}}{{}}{{{num}}}{{{den}}}"
            return rf"\frac{{{num}}}{{{den}}}"
        if tag == "sSup":
            return f"{{{self.arg(el, 'e')}}}^{{{self.arg(el, 'sup')}}}"
        if tag == "sSub":
            return f"{{{self.arg(el, 'e')}}}_{{{self.arg(el, 'sub')}}}"
        if tag == "sSubSup":
            return f"{{{self.arg(el, 'e')}}}_{{{self.arg(el, 'sub')}}}^{{{self.arg(el, 'sup')}}}"
        if tag == "sPre":
            return f"{{}}_{{{self.arg(el, 'sub')}}}^{{{self.arg(el, 'sup')}}}{{{self.arg(el, 'e')}}}"
        if tag == "d":
            beg = self.val(el, "m:dPr/m:begChr", default="(")
            end = self.val(el, "m:dPr/m:endChr", default=")")
            sep = self.val(el, "m:dPr/m:sepChr", default="|")
            parts = [self.kids(e) for e in el.findall("m:e", NS)]
            sep_tex = {"|": r" \mid ", ",": ", "}.get(sep, SYMBOLS.get(sep, sep))
            inner = sep_tex.join(parts)
            if beg in ("(", "[", "{") and end in (")", "]", "}") and "\\frac" not in inner \
                    and "\\sum" not in inner:
                return f"{DELIM.get(beg, beg)}{inner}{DELIM.get(end, end)}"
            lb, rb = DELIM.get(beg, beg), DELIM.get(end, end)
            return rf"\left{lb} {inner} \right{rb} "
        if tag == "nary":
            chr_ = self.val(el, "m:naryPr/m:chr", default="∫")
            op = NARY.get(chr_, SYMBOLS.get(chr_, chr_).strip())
            sub = "" if self.val(el, "m:naryPr/m:subHide") in ("1", "on") else self.arg(el, "sub")
            sup = "" if self.val(el, "m:naryPr/m:supHide") in ("1", "on") else self.arg(el, "sup")
            s = op + (f"_{{{sub}}}" if sub else "") + (f"^{{{sup}}}" if sup else "")
            return s + " " + self.arg(el, "e")
        if tag == "rad":
            deg = self.arg(el, "deg")
            hide = self.val(el, "m:radPr/m:degHide") in ("1", "on")
            return (rf"\sqrt[{deg}]" if deg and not hide else r"\sqrt") + f"{{{self.arg(el, 'e')}}}"
        if tag == "acc":
            ch = self.val(el, "m:accPr/m:chr", default="\u0302")
            return f"{ACCENT.get(ch, r'\hat')}{{{self.arg(el, 'e')}}}"
        if tag == "bar":
            pos = self.val(el, "m:barPr/m:pos", default="bot")
            return (r"\overline" if pos == "top" else r"\underline") + f"{{{self.arg(el, 'e')}}}"
        if tag == "groupChr":
            pos = self.val(el, "m:groupChrPr/m:pos", default="bot")
            return (r"\overbrace" if pos == "top" else r"\underbrace") + f"{{{self.arg(el, 'e')}}}"
        if tag == "func":
            name = self.arg(el, "fName").strip()
            if re.fullmatch(r"\\mathrm\{(\w+)\}", name):
                w = re.fullmatch(r"\\mathrm\{(\w+)\}", name).group(1)
                name = ("\\" + w) if w in FUNCS else rf"\operatorname{{{w}}}"
            return f"{name} {self.arg(el, 'e')}"
        if tag == "limLow":
            e = self.arg(el, "e").strip()
            if e.startswith("\\lim") or e.startswith("\\min") or e.startswith("\\max"):
                return f"{e}_{{{self.arg(el, 'lim')}}}"
            return rf"\underset{{{self.arg(el, 'lim')}}}{{{e}}}"
        if tag == "limUpp":
            return rf"\overset{{{self.arg(el, 'lim')}}}{{{self.arg(el, 'e')}}}"
        if tag == "eqArr":
            rows = [self.kids(e) for e in el.findall("m:e", NS)]
            return r"\begin{aligned}" + r" \\ ".join(rows) + r"\end{aligned}"
        if tag == "m":
            rows = [" & ".join(self.kids(e) for e in mr.findall("m:e", NS)) for mr in el.findall("m:mr", NS)]
            return r"\begin{matrix}" + r" \\ ".join(rows) + r"\end{matrix}"
        self.todo.append(tag)
        return self.kids(el)


def tidy_math(s: str) -> str:
    s = re.sub(r"\{([A-Za-z0-9])\}(?=[_^])", r"\1", s)        # {a}^{2} -> a^{2}
    s = re.sub(r"\{(\\[A-Za-z]+)\s*\}(?=[_^])", r"\1", s)     # {\log }_2 -> \log_2
    s = re.sub(r"([_^])\{([A-Za-z0-9])\}", r"\1\2", s)        # a^{2} -> a^2
    s = re.sub(r"[ ]{2,}", " ", s)
    s = re.sub(r"\\([A-Za-z]+) (?=[^A-Za-z ])", r"\\\1", s)     # "\cdot (" -> "\cdot("
    s = re.sub(r"^(~|\\[ ,;])+|(~|\\[ ,;])+$", "", s.strip())
    s = re.sub(r"\\text\{\s*\}", "", s)
    return s.strip()


# --- slides -------------------------------------------------------------------------------


P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A14 = "{%s}" % NS["a14"]
R_EMBED = "{%s}embed" % NS["r"]


def math_tex(mel, omml: Omml) -> tuple[list[str], bool]:
    """a14:m element -> LaTeX pieces; display if it holds an m:oMathPara."""
    parts, display = [], False
    for node in mel:
        body = tidy_math(omml.conv(node)) if node.tag in (M + "oMathPara", M + "oMath") else ""
        if not body:
            continue
        if node.tag == M + "oMathPara":
            display = True
            parts.append(r"\[" + body + r"\]")
        else:
            parts.append("$" + body + "$")
    return parts, display


def add_math(parts: list[str], pieces: list[str]) -> None:
    for piece in pieces:
        if parts and parts[-1].endswith("$") and piece.startswith("$"):
            parts.append(r"\quad ")   # two formulas side by side (tab-separated in the deck)
        parts.append(piece)


def paragraph_tex(p, omml: Omml) -> tuple[str, bool]:
    """LaTeX of one a:p (text runs + inline/display math); returns (tex, is_display)."""
    parts, display = [], False
    for child in p:
        tag = child.tag
        if tag == A + "r":
            t = child.find("a:t", NS)
            text = t.text if t is not None and t.text else ""
            rpr = child.find("a:rPr", NS)
            s = esc_text(text)
            if rpr is not None and rpr.get("b") == "1" and s.strip():
                s = r"\textbf{" + s + "}"
            elif rpr is not None and rpr.get("i") == "1" and s.strip():
                s = r"\emph{" + s + "}"
            parts.append(s)
        elif tag == A + "br":
            parts.append(r"\\ ")
        elif tag == A + "fld":
            t = child.find("a:t", NS)
            parts.append(esc_text(t.text if t is not None and t.text else ""))
        elif tag == A14 + "m":
            ps, d = math_tex(child, omml)
            add_math(parts, ps)
            display |= d
        elif tag == MC + "AlternateContent":
            choice = child.find("mc:Choice", NS)
            mel = choice.find(".//a14:m", NS) if choice is not None else None
            if mel is None:
                parts.append("% TODO: alternate content without math\n")
                continue
            ps, d = math_tex(mel, omml)
            add_math(parts, ps)
            display |= d
    tex = "".join(parts).strip()
    return tex, display


def p_level(p) -> int:
    ppr = p.find("a:pPr", NS)
    return int(ppr.get("lvl", "0")) if ppr is not None else 0


def body_tex(txbody, omml: Omml) -> list[str]:
    lines: list[str] = []
    depth = -1
    for p in txbody.findall("a:p", NS):
        tex, display = paragraph_tex(p, omml)
        if not tex:
            continue
        lvl = p_level(p)
        while depth < lvl:
            depth += 1
            lines.append("  " * (depth + 1) + r"\begin{itemize}")
        while depth > lvl:
            lines.append("  " * (depth + 1) + r"\end{itemize}")
            depth -= 1
        ind = "  " * (depth + 2)
        if tex.startswith("["):
            tex = "{}" + tex
        if display and tex.startswith(r"\[") and tex.endswith(r"\]"):
            lines.append(ind + r"\item[] " + tex)
        else:
            lines.append(ind + r"\item " + tex)
    while depth >= 0:
        lines.append("  " * (depth + 1) + r"\end{itemize}")
        depth -= 1
    return lines


def plain_tex(txbody, omml: Omml) -> str:
    return r" \\ ".join(t for t, _ in (paragraph_tex(p, omml) for p in txbody.findall("a:p", NS)) if t)


def placeholder_kind(sp) -> str | None:
    ph = sp.find(f"{P}nvSpPr/{P}nvPr/{P}ph")
    if ph is None:
        return None
    t = ph.get("type", "body")
    if t in ("title", "ctrTitle"):
        return "title"
    if t == "subTitle":
        return "subtitle"
    if t in ("dt", "ftr", "sldNum", "hdr"):
        return "skip"
    return "body"


def iter_shapes(tree):
    """Shape elements in z-order, descending into groups and taking the a14
    choice of mc:AlternateContent (shapes that contain equations)."""
    for el in tree:
        if el.tag == P + "grpSp":
            yield from iter_shapes(el)
        elif el.tag == MC + "AlternateContent":
            choice = el.find("mc:Choice", NS)
            if choice is not None:
                yield from iter_shapes(choice)
        elif el.tag in (P + "sp", P + "pic"):
            yield el


def convert(pptx: Path, lecture_dir: Path, lecture: int, title: str | None) -> tuple[str, list[str]]:
    prs = Presentation(str(pptx))
    img_dir = lecture_dir / "img"
    report: list[str] = []
    frames: list[str] = []
    deck_title, seen_images = title, {}
    slide_h = int(prs.slide_height or 1)
    # small pictures that appear on 3+ slides are decorations (the "?" callout icon)
    usage: dict[str, set[int]] = {}
    small: set[str] = set()
    for k, slide in enumerate(prs.slides, 1):
        for el in iter_shapes(slide.shapes._spTree):
            blip = el.find(".//a:blip", NS) if el.tag == P + "pic" else None
            if blip is not None:
                part = slide.part.related_part(blip.get(R_EMBED))
                usage.setdefault(str(part.partname), set()).add(k)
                try:
                    if max(Image.from_blob(part.blob).size) <= 256:
                        small.add(str(part.partname))
                except Exception:
                    pass
    decorative = {name for name, ks in usage.items() if len(ks) >= 3 and name in small}
    for k, slide in enumerate(prs.slides, 1):
        omml = Omml()
        frame_title, body, asides, pics, notes = "", [], [], [], []
        for el in iter_shapes(slide.shapes._spTree):
            if el.tag == P + "pic":
                blip = el.find(".//a:blip", NS)
                part = slide.part.related_part(blip.get(R_EMBED)) if blip is not None else None
                if part is None:
                    continue
                if str(part.partname) in decorative:
                    continue
                ext = part.partname.ext
                name = seen_images.get(part.partname)
                if name is None:
                    name = f"slide{k:02d}-{len(pics) + 1}.{ext}"
                    img_dir.mkdir(parents=True, exist_ok=True)
                    (img_dir / name).write_bytes(part.blob)
                    seen_images[part.partname] = name
                ext_el = el.find(".//a:xfrm/a:ext", NS)
                h = int(ext_el.get("cy")) if ext_el is not None else slide_h // 3
                frac = min(0.8, max(0.08, h / slide_h))
                pics.append(rf"\includegraphics[height={frac:.2f}\textheight]{{img/{name}}}"
                            "  % TODO: picture (diagram? formula? handwriting?)")
                continue
            kind = placeholder_kind(el)
            txbody = el.find(f"{P}txBody")
            if kind == "skip" or txbody is None:
                continue
            if kind == "title":
                frame_title = plain_tex(txbody, omml)
            elif kind == "subtitle":
                body.append("  " + plain_tex(txbody, omml))
            elif kind == "body":
                body += body_tex(txbody, omml)
            else:
                t = plain_tex(txbody, omml)
                if t:
                    asides.append(t)
        if slide.has_notes_slide:
            for line in slide.notes_slide.notes_text_frame.text.splitlines():
                if line.strip():
                    notes.append("  % note: " + line.strip())
        if k == 1 and deck_title is None:
            deck_title = frame_title
            continue
        out = [f"% --- slide {k} ---", rf"\begin{{canvasframe}}{{{frame_title}}}"]
        out += body
        for t in asides:
            out.append(r"  \aside{" + t + "}")
        for p in pics:
            out.append("  " + p)
        if omml.todo:
            out.append(f"  % TODO: untranslated OMML elements: {', '.join(sorted(set(omml.todo)))}")
            report.append(f"slide {k}: OMML {sorted(set(omml.todo))}")
        out += notes
        out.append(r"\end{canvasframe}")
        frames.append("\n".join(out))
        report.append(f"slide {k}: {frame_title!r}, {len(body)} body lines, {len(asides)} asides, "
                      f"{len(pics)} pictures")
    head = [
        f"% Converted from {pptx.name} by scripts/pptx2beamer.py; reviewed by hand.",
        r"\documentclass{ca-slides}",
        "",
        rf"\lecture{{{lecture}}}{{{deck_title or 'TODO'}}}",
        r"\author{}",
        "",
        r"\begin{document}",
        r"\titleframe",
        "",
    ]
    return "\n".join(head) + "\n\n".join(frames) + "\n\\end{document}\n", report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pptx", type=Path)
    ap.add_argument("lecture_dir", type=Path)
    ap.add_argument("--lecture", type=int, default=None,
                    help="lecture number (default: from the NN- prefix of lecture_dir)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--out", default="slides-skeleton.tex",
                    help="file name inside lecture_dir (default: slides-skeleton.tex)")
    a = ap.parse_args(argv)
    n = a.lecture
    if n is None:
        m = re.match(r"(\d+)-", a.lecture_dir.name)
        n = int(m.group(1)) if m else 0
    a.lecture_dir.mkdir(parents=True, exist_ok=True)
    tex, report = convert(a.pptx, a.lecture_dir, n, a.title)
    (a.lecture_dir / a.out).write_text(tex, encoding="utf-8")
    for line in report:
        print(line)
    print(f"wrote {a.lecture_dir / a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
