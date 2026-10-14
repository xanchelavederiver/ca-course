"""scripts/pptx2beamer.py: OMML -> LaTeX translation and text escaping."""

import importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

pytest.importorskip("pptx")

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "pptx2beamer.py"
spec = importlib.util.spec_from_file_location("pptx2beamer", SCRIPT)
p2b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p2b)

M = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'


def omml(inner: str) -> str:
    el = ET.fromstring(f"<m:oMath {M}>{inner}</m:oMath>")
    conv = p2b.Omml()
    out = p2b.tidy_math(conv.conv(el))
    assert conv.todo == []
    return out


def r(text: str, sty: str | None = None) -> str:
    rpr = f'<m:rPr><m:sty m:val="{sty}"/></m:rPr>' if sty else ""
    return f"<m:r>{rpr}<m:t>{text}</m:t></m:r>"


def test_runs_and_unicode_math_letters():
    assert omml(r("𝑎") + r("+") + r("𝑏")) == "a+b"
    assert omml(r("𝜇")) == r"\mu"
    assert omml(r("ℒ") + r("(𝑥)")) == r"\mathcal{L}(x)"
    assert omml(r("max", "p")) == r"\max"
    assert omml(r("𝑥") + r("≤") + r("𝑦")) == r"x\le y"


def test_structures():
    assert omml(f"<m:f><m:num>{r('a')}</m:num><m:den>{r('b')}</m:den></m:f>") == r"\frac{a}{b}"
    assert omml(f"<m:sSup><m:e>{r('x')}</m:e><m:sup>{r('2')}</m:sup></m:sSup>") == "x^2"
    assert omml(f"<m:sSub><m:e>{r('a')}</m:e><m:sub>{r('i')}</m:sub></m:sSub>") == "a_i"
    nary = (f'<m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr><m:sub>{r("i=0")}</m:sub>'
            f'<m:sup>{r("N")}</m:sup><m:e>{r("x")}</m:e></m:nary>')
    assert omml(nary) == r"\sum_{i=0}^N x"
    assert omml(f"<m:rad><m:radPr><m:degHide m:val=\"1\"/></m:radPr><m:deg/><m:e>{r('n')}</m:e></m:rad>") \
        == r"\sqrt{n}"
    floor = (f'<m:d><m:dPr><m:begChr m:val="⌊"/><m:endChr m:val="⌋"/></m:dPr>'
             f'<m:e>{r("B/2")}</m:e></m:d>')
    assert omml(floor) == r"\left\lfloor B/2 \right\rfloor"
    # a brace opening a system has no closing delimiter
    system = f'<m:d><m:dPr><m:begChr m:val="{{"/><m:endChr m:val=""/></m:dPr><m:e>{r("x")}</m:e></m:d>'
    assert omml(system) == r"\left\{ x \right."
    log2 = f"<m:sSub><m:e>{r('log', 'p')}</m:e><m:sub>{r('2')}</m:sub></m:sSub>"
    assert omml(log2) == r"\log_2"


def test_text_escaping():
    assert p2b.esc_text("50% & $x_1$ — «ок»") == r"50\% \& \$x\_1\$ --- «ок»"
    assert p2b.esc_text("a ≤ b") == r"a $\le$ b"
