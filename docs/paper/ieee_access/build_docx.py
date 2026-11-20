"""
Build a Word version of the IEEE Access draft from main.tex.

    python docs/paper/ieee_access/build_docx.py <new file.docx>

Since 18 Oct 2026 the authors edit VaultTrust_IEEE_Access.docx by hand; it is the master copy and main.tex is
no longer kept in sync. This script therefore refuses to write over an existing file: give it a new path
(for example to start a fresh draft from the LaTeX text).

Two-column IEEE Access-like layout (US Letter, Times New Roman 10 pt), native Word equations, numbered
figures/tables/references, references renumbered in order of first citation (IEEE rule). "%% TODO"
comments in main.tex appear as yellow-highlighted notes. This is an editable draft; for submission
paste it into the official IEEE Access Word template (or submit the LaTeX version).
Understands only the LaTeX subset used in main.tex.
"""

import os
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "main.tex")

FONT = "Times New Roman"
BLUE = RGBColor(0x00, 0x5A, 0x9C)
PAGE_W, MARGIN_LR, GAP = 8.5, 0.65, 0.25
COL_W = (PAGE_W - 2 * MARGIN_LR - GAP) / 2

BULLET = "•\t"
ROMAN = ["I","II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

# ----------------------------------------------------------------------------------------------------
# text conversion
# ----------------------------------------------------------------------------------------------------
ACCENTS = {("'", "a"): "á", ("'", "e"): "é", ("v", "C"): "Č", ("v", "c"): "č", ("c", "c"): "ç",
           ('"', "o"): "ö", ("'", "o"): "ó"}
TEXT_MACROS = {"pct": "%", "%": "%", "$": "$", "&": "&", "_": "_", ",": "\u202f", "dots": "…",
               "headeretal": "et al.", "LaTeX": "LaTeX", " ": " ", "\n": " ", "\\": " "}
MATH_SYM = {"psi": "ψ", "theta": "θ", "Delta": "Δ", "pi": "π", "sigma": "σ", "tau": "τ", "chi": "χ",
            "times": "×", "pm": "±", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "in": "∈", "to": "→",
            "dots": "…", "cdots": "⋯", "Vert": "‖", "lVert": "‖", "rVert": "‖", "mid": "|", "lfloor": "⌊",
            "rfloor": "⌋", "top": "⊤", "wedge": "∧", "circ": "°", ",": "\u2009", ";": " ", "!": "",
            "%": "%", "_": "_", "{": "{", "}": "}", "max": "max", "bmod": "mod"}
UPRIGHT_WORDS = {"max", "mod"}
RELATIONS = set("=<>≤≥∈→×±∧")


def strip_comments(tex):
    """Drop % comments; keep '%% TODO' comments as \\todo{...} markers."""
    out, lines = [], tex.splitlines()
    for n, line in enumerate(lines):
        m = re.search(r"(?<!\\)%", line)
        if not m:
            out.append(line)
            continue
        code, comment = line[:m.start()], line[m.start():]
        t = re.search(r"TODO\s*:?\s*(.*)", comment)
        if t:
            note = t.group(1).strip()
            k = n + 1                      # a TODO may continue on following comment-only lines
            while k < len(lines) and re.match(r"\s*%%(?!.*TODO)", lines[k]) and not code.strip():
                note += " " + lines[k].strip().lstrip("%").strip()
                k += 1
            note = note.replace("{", "(").replace("}", ")") or "complete this"
            code = code.rstrip() + " \\todo{" + note + "}"
        out.append(code)
    return "\n".join(out)


def group(s, i):
    """Return (content, index after) of the {...} group starting at s[i] == '{'."""
    assert s[i] == "{", s[i:i + 30]
    depth, j = 0, i
    while True:
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1


class Ctx:
    def __init__(self):
        self.refs, self.cites = {}, {}


CTX = Ctx()


def cite_text(keys):
    nums = sorted(CTX.cites[k] for k in keys)
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(f"[{nums[i]}]–[{nums[j]}]" if j - i >= 2 else ", ".join(f"[{n}]" for n in nums[i:j + 1]))
        i = j + 1
    return ", ".join(parts)


def inline(s, fmt=None):
    """LaTeX text -> list of (text, fmt) runs."""
    fmt = dict(fmt or {})
    runs, i, buf = [], 0, []

    def flush():
        if buf:
            runs.append(("".join(buf), dict(fmt)))
            buf.clear()

    while i < len(s):
        c = s[i]
        if c == "$":
            j = s.index("$", i + 1)
            flush()
            mr = [(t, f) for t, f in math_runs(s[i + 1:j], fmt) if t]
            if mr:                         # no doubled spaces where text and math meet
                if runs and runs[-1][0].endswith((" ", " ")):
                    mr[0] = (mr[0][0].lstrip(" "), mr[0][1])
                if j + 1 < len(s) and s[j + 1] in " \n":
                    mr[-1] = (mr[-1][0].rstrip(" "), mr[-1][1])
            runs.extend(mr)
            i = j + 1
        elif c == "\\":
            m = re.match(r"\\([a-zA-Z]+|.)", s[i:], re.S)
            if not m:                      # lone backslash at the very end
                break
            name = m.group(1)
            i += len(m.group(0))
            if name in ("emph", "textit", "textbf", "texttt", "uppercase", "todo", "url"):
                while i < len(s) and s[i] == " ":
                    i += 1
                arg, i = group(s, i)
                flush()
                sub = dict(fmt)
                if name in ("emph", "textit"):
                    sub["italic"] = not fmt.get("italic")
                elif name == "textbf":
                    sub["bold"] = True
                elif name in ("texttt", "url"):
                    sub["mono"] = True
                elif name == "uppercase":
                    arg = arg.upper()
                elif name == "todo":
                    runs.append((f" [TODO: {arg}] ", dict(fmt, todo=True)))
                    continue
                runs.extend(inline(arg, sub))
            elif name in ("cite", "ref"):
                arg, i = group(s, i)
                keys = [k.strip() for k in arg.split(",")]
                buf.append(cite_text(keys) if name == "cite" else CTX.refs.get(keys[0], "??"))
            elif name in ("'", "v", "c", '"') and i < len(s):
                if s[i] == "{":
                    arg, i = group(s, i)
                else:
                    arg, i = s[i], i + 1
                buf.append(ACCENTS.get((name, arg), arg))
            elif name in TEXT_MACROS:
                buf.append(TEXT_MACROS[name])
            elif name in ("label", "footnotesize"):
                if i < len(s) and s[i] == "{":
                    _, i = group(s, i)
            else:
                buf.append(name)
        elif c == "~":
            buf.append("\u00a0")
            i += 1
        elif s.startswith("---", i):
            buf.append("—")
            i += 3
        elif s.startswith("--", i):
            buf.append("–")
            i += 2
        elif s.startswith("``", i):
            buf.append("“")
            i += 2
        elif s.startswith("''", i):
            buf.append("”")
            i += 2
        elif c == "`":
            buf.append("‘")
            i += 1
        elif c == "'":
            buf.append("’")
            i += 1
        elif c in "{}":
            i += 1
        elif c in " \n\t":
            if not (buf and buf[-1] in (" ", "\u00a0")) and not (not buf and runs and runs[-1][0].endswith(" ")):
                buf.append(" ")
            while i < len(s) and s[i] in " \n\t":
                i += 1
        else:
            buf.append(c)
            i += 1
    flush()
    return runs


def math_runs(s, base):
    """Inline LaTeX math -> runs (italic Latin letters, sub/superscripts, Unicode symbols)."""
    out = []

    def emit(text, **f):
        out.append((text, dict(base, **f)))

    def last_is_operand():
        for t, _ in reversed(out):
            if t.strip():
                return not (t.strip()[-1] in RELATIONS or t.strip()[-1] in "(,[|−+")
        return False

    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+|.)", s[i:], re.S)
            if not m:
                break
            name = m.group(1)
            i += len(m.group(0))
            if name in ("bar",):
                arg, i = group(s, i)
                sym = MATH_SYM.get(arg.lstrip("\\"), arg)
                emit(sym + "\u0304", italic=sym.isalpha() and sym.isascii() or sym in "ψθ")
            elif name in ("mathbf",):
                arg, i = group(s, i)
                emit(arg, bold=True, italic=False)
            elif name == "mathbb":
                arg, i = group(s, i)
                emit({"R": "ℝ"}.get(arg, arg), italic=False)
            elif name == "mathit":
                arg, i = group(s, i)
                emit(arg.replace("\\_", "_"), italic=True)
            elif name in ("text", "mathrm", "operatorname"):
                arg, i = group(s, i)
                emit(arg, italic=False)
            elif name == "texttt":
                arg, i = group(s, i)
                emit(arg, italic=False, mono=True)
            elif name in MATH_SYM:
                sym = MATH_SYM[name]
                if sym in RELATIONS:
                    emit(f" {sym} ", italic=False)
                else:
                    emit(sym, italic=sym in "ψθπστχ" or False)
            else:
                emit(name, italic=False)
        elif c in "^_":
            i += 1
            if s[i] == "{":
                arg, i = group(s, i)
            elif s[i] == "\\":
                m = re.match(r"\\([a-zA-Z]+)", s[i:])
                arg, i = m.group(0), i + len(m.group(0))
                if i < len(s) and s[i] == "{":          # \text{...}, \mathbf{...} as a sub/superscript
                    g, i = group(s, i)
                    arg += "{" + g + "}"
            else:
                arg, i = s[i], i + 1
            if arg == "\\circ":
                emit("°", italic=False)
                continue
            for t, f in math_runs(arg, base):
                f["vert"] = "superscript" if c == "^" else "subscript"
                out.append((t.strip(), f))
        elif c in "=<>":
            emit(f" {c} ", italic=False)
            i += 1
        elif c in "+-":
            sym = "−" if c == "-" else "+"
            emit(f" {sym} " if last_is_operand() else sym, italic=False)
            i += 1
        elif c == "'":
            emit("′", italic=False)
            i += 1
        elif c in "{}":
            i += 1
        elif c in " \n\t":
            i += 1
        elif c == ",":
            emit(", " if i + 1 < len(s) else ",", italic=False)
            i += 1
        elif c.isalpha():
            emit(c, italic=True)
            i += 1
        else:
            emit(c, italic=False)
            i += 1
    return out


# ----------------------------------------------------------------------------------------------------
# OMML display equations (in the order they appear in main.tex)
# ----------------------------------------------------------------------------------------------------
def R(t, sty=None):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    pr = f'<m:rPr><m:sty m:val="{sty}"/></m:rPr>' if sty else ""
    return f'<m:r>{pr}<m:t xml:space="preserve">{t}</m:t></m:r>'


def P(t):
    return R(t, "p")


def B(t):
    return R(t, "b")


def T(t):
    """Ordinary text inside an equation (no operator spacing, so hyphens stay hyphens)."""
    return f'<m:r><m:rPr><m:nor/></m:rPr><m:t xml:space="preserve">{t}</m:t></m:r>'


def sub(b, s):
    return f"<m:sSub><m:e>{b}</m:e><m:sub>{s}</m:sub></m:sSub>"


def sup(b, s):
    return f"<m:sSup><m:e>{b}</m:e><m:sup>{s}</m:sup></m:sSup>"


def frac(n, d):
    return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"


def delim(inner, beg="(", end=")"):
    return f'<m:d><m:dPr><m:begChr m:val="{beg}"/><m:endChr m:val="{end}"/></m:dPr><m:e>{inner}</m:e></m:d>'


def limlow(base, lim):
    return f"<m:func><m:fName><m:limLow><m:e>{base}</m:e><m:lim>{lim}</m:lim></m:limLow></m:fName><m:e></m:e></m:func>"


def func(name, arg):
    return f"<m:func><m:fName>{P(name)}</m:fName><m:e>{arg}</m:e></m:func>"


SP = P("\u2003")
EQUATIONS = [
    # (1) yaw and pitch
    R("ψ") + P("=") + func("atan2", delim(sub(R("R"), P("02")) + P(",") + sub(R("R"), P("22")))) + P(",") + SP
    + R("θ") + P("=") + func("arcsin", delim(P("−") + sub(R("R"), P("12")))),
    # (2) PAD score
    sub(R("p"), R("F")) + P("=") + limlow(P("median"), R("i") + P("=1,…,10"))
    + R("P") + delim(P("real") + P("∣") + sub(R("x"), R("i"))) + P(",") + SP
    + R("F") + P("=") + delim(sub(R("p"), R("F")) + P("≥") + sub(R("τ"), R("F")), "[", "]"),
    # (3) logistic map
    sub(R("x"), R("n") + P("+1")) + P("=") + R("r") + sub(R("x"), R("n")) + delim(P("1−") + sub(R("x"), R("n"))),
    # (4) template and match
    B("t") + P("=") + frac(B("W") + sub(B("e"), R("π")), delim(B("W") + sub(B("e"), R("π")), "‖", "‖"))
    + P(",") + SP + R("A") + P("=") + delim(sup(B("t"), P("′⊤")) + B("t") + P("≥0.40"), "[", "]"),
    # (5) fusion
    R("D") + P("=") + R("L") + P("∧") + R("C") + P("∧") + R("F") + P("∧") + R("A"),
    # (6) OTP seed
    R("σ") + P("=") + T("HMAC-SHA256") + delim(R("K") + P(", ") + sub(R("T"), P("[8]")) + P(" ‖ ")
                                                    + T("SHA256") + delim(R("ctx"))),
    # (7) OTP code, two lines
    [R("h") + P("=") + T("SHA256") + delim(T("walk-otp-v2") + P("‖") + sub(R("v"), P("0"))
                                           + P("‖⋯‖") + sub(R("v"), P("16"))) + P(","),
     R("OTP") + P("=") + func("DT", delim(R("h"))) + P(" mod ") + sup(P("10"), P("6")) + P(",")],
]
M_NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'


# ----------------------------------------------------------------------------------------------------
# document helpers
# ----------------------------------------------------------------------------------------------------
def add_runs(par, runs, size=10, color=None):
    for text, f in runs:
        if not text:
            continue
        r = par.add_run(text)
        r.font.name = "Courier New" if f.get("mono") else FONT
        r.font.size = Pt(size * (0.92 if f.get("mono") else 1))
        r.italic = f.get("italic") or None
        r.bold = f.get("bold") or None
        if f.get("vert") == "superscript":
            r.font.superscript = True
        elif f.get("vert") == "subscript":
            r.font.subscript = True
        if f.get("todo"):
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            r.font.size = Pt(size * 0.85)
        if color is not None:
            r.font.color.rgb = color
    return par


def para(doc, text="", size=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0.17, after=0, before=0, keep=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.first_line_indent = Inches(indent) if indent else None
    pf.space_after, pf.space_before = Pt(after), Pt(before)
    pf.line_spacing = 1.0
    if keep:
        pf.keep_with_next = True
    if text:
        add_runs(p, inline(text) if isinstance(text, str) else text, size)
    return p


def border(p, sides=("top", "bottom"), sz=6, color="7F7F7F"):
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    for side in sides:
        e = OxmlElement(f"w:{side}")
        for k, v in (("val", "single"), ("sz", str(sz)), ("space", "4"), ("color", color)):
            e.set(qn(f"w:{k}"), v)
        bdr.append(e)
    pPr.append(bdr)


def heading(doc, text, level):
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT, before=8 if level == 1 else 5, after=3, keep=True)
    add_runs(p, [(t.upper(), dict(f, bold=(level == 1))) for t, f in inline(text)],
             size=10 if level == 1 else 9.5, color=BLUE)
    return p


def set_cols(section, n):
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sectPr.append(cols)
    cols.set(qn("w:num"), str(n))
    cols.set(qn("w:space"), str(int(GAP * 1440)))


def field(par, instr, size=8):
    for kind, text in (("begin", None), (None, instr), ("separate", None), (None, "1"), ("end", None)):
        r = par.add_run()
        r.font.size, r.font.name = Pt(size), FONT
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._r.append(fc)
        elif text == instr:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = f" {instr} "
            r._r.append(it)
        else:
            r.text = text


def cell_text(cell, runs, size=8, align=WD_ALIGN_PARAGRAPH.CENTER):
    p = cell.paragraphs[0]
    p.paragraph_format.alignment = align
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    add_runs(p, runs, size)


def cell_borders(cell, top=None, bottom=None):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for side, sz in (("top", top), ("bottom", bottom)):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single" if sz else "nil")
        if sz:
            e.set(qn("w:sz"), str(sz))
            e.set(qn("w:color"), "000000")
        b.append(e)
    for side in ("left", "right", "insideV"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "nil")
        b.append(e)
    tcPr.append(b)


def cell_width(cell, inches):
    tcPr = cell._tc.get_or_add_tcPr()
    w = OxmlElement("w:tcW")
    w.set(qn("w:w"), str(int(inches * 1440)))
    w.set(qn("w:type"), "dxa")
    tcPr.append(w)


# ----------------------------------------------------------------------------------------------------
# parsing main.tex
# ----------------------------------------------------------------------------------------------------
def env_blocks(body):
    """Split the body into a sequence of ('cmd'|'env'|'text', ...) blocks."""
    blocks, i = [], 0
    pat = re.compile(r"\\(section\*?|subsection|begin)\{|\n\s*\n")
    text_start = 0
    while True:
        m = pat.search(body, i)
        if not m:
            blocks.append(("text", body[text_start:]))
            break
        if m.group(0).strip() == "":
            blocks.append(("text", body[text_start:m.start()]))
            i = text_start = m.end()
            continue
        blocks.append(("text", body[text_start:m.start()]))
        kind = m.group(1)
        arg, j = group(body, m.end() - 1)
        if kind == "begin":
            end = body.index(f"\\end{{{arg}}}", j)
            blocks.append(("env", arg, body[j:end]))
            i = text_start = end + len(f"\\end{{{arg}}}")
        else:
            label = re.match(r"\s*\\label\{([^}]+)\}", body[j:])
            if label:
                j += label.end()
            blocks.append((kind, arg, label.group(1) if label else None))
            i = text_start = j
    return [b for b in blocks if not (b[0] == "text" and not b[1].strip())]


def number_labels(blocks):
    sec = subsec = fig = tab = eq = 0
    for b in blocks:
        if b[0] == "section":
            sec, subsec = sec + 1, 0
            if b[2]:
                CTX.refs[b[2]] = ROMAN[sec - 1]
        elif b[0] == "subsection":
            subsec += 1
            if b[2]:
                CTX.refs[b[2]] = f"{ROMAN[sec - 1]}-{chr(64 + subsec)}"
        elif b[0] == "env":
            lab = re.search(r"\\label\{([^}]+)\}", b[2])
            if b[1] in ("figure", "figure*"):
                fig += 1
                if lab:
                    CTX.refs[lab.group(1)] = str(fig)
            elif b[1] == "table":
                tab += 1
                if lab:
                    CTX.refs[lab.group(1)] = str(tab)
            elif b[1] == "equation":
                eq += 1
    return eq


_FONTS = {}


def text_width(text, bold=False, size=7.5):
    """Printed width in inches of text in Times New Roman (falls back to an average character width)."""
    try:
        from PIL import ImageFont
        if bold not in _FONTS:
            _FONTS[bold] = ImageFont.truetype(r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf", 100)
        return _FONTS[bold].getlength(text) / 100 * size / 72
    except OSError:
        return len(text) * 0.058 * size / 7.5


def tabular(doc, spec, content):
    widths = [float(w) for w in re.findall(r"p\{([\d.]+)cm\}", spec)]
    ncols = len(widths) + len(re.findall(r"[lcr]", re.sub(r"p\{[^}]*\}", "", spec)))
    rows, rule_after = [], set()
    for chunk in re.split(r"\\\\(?:\[[^\]]*\])?", content):
        chunk = chunk.strip()
        while True:
            m = re.match(r"\\(toprule|midrule|bottomrule|hline)", chunk)
            if not m:
                break
            if m.group(1) == "midrule":
                rule_after.add(len(rows) - 1)
            chunk = chunk[m.end():].strip()
        if chunk:
            cells = re.split(r"(?<!\\)&", chunk)
            cells = [re.sub(r"\\multirow\{\d+\}\{\*\}\{(.*)\}", r"\1", c.strip()) for c in cells]
            rows.append(cells)
    header_end = min(rule_after) if rule_after else 0
    if widths:
        scale = COL_W / sum(w / 2.54 for w in widths)
        col_in = [w / 2.54 * scale for w in widths]
    else:
        # size columns from their content (Times New Roman metrics): never break a word, share the rest
        pad = 0.09
        plain = [[("".join(t for t, _ in inline(r[c] if c < len(r) else "")), r_i <= header_end)
                  for r_i, r in enumerate(rows)] for c in range(ncols)]
        need = [max(text_width(w, bold) for cell, bold in col for w in (cell.split() or [""])) + pad
                for col in plain]
        extra = [max(text_width(cell, bold) for cell, bold in col) + pad - n for col, n in zip(plain, need)]
        spare = COL_W - sum(need)
        if spare > 0:
            share = sum(max(e, 0) for e in extra) or 1
            col_in = [n + spare * max(e, 0) / share for n, e in zip(need, extra)]
        else:
            col_in = [n * COL_W / sum(need) for n in need]
    t = doc.add_table(rows=len(rows), cols=ncols)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for c_i, w in enumerate(col_in):                # grid widths must agree with the cell widths
        t.columns[c_i].width = Inches(w)
    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    mar = parse_xml('<w:tblCellMar xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    '<w:left w:w="45" w:type="dxa"/><w:right w:w="45" w:type="dxa"/></w:tblCellMar>')
    tblPr.append(mar)
    for r_i, row in enumerate(rows):
        for c_i in range(ncols):
            cell = t.cell(r_i, c_i)
            cell_width(cell, col_in[c_i])
            txt = row[c_i] if c_i < len(row) else ""
            left = bool(widths) or c_i == 0
            cell_text(cell, inline(txt), size=7.5, align=WD_ALIGN_PARAGRAPH.LEFT if left else WD_ALIGN_PARAGRAPH.CENTER)
            cell.paragraphs[0].paragraph_format.keep_with_next = r_i < len(rows) - 1   # keep the table in one piece
            cell_borders(cell, top=12 if r_i == 0 else None,
                         bottom=12 if r_i == len(rows) - 1 else (6 if r_i in rule_after else None))
            if r_i <= header_end:
                for run in cell.paragraphs[0].runs:
                    run.bold = True
    return t


def caption(doc, kind, num, text, before=2, after=8):
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT if kind == "FIGURE" else WD_ALIGN_PARAGRAPH.CENTER,
             before=before, after=after, keep=(kind == "TABLE"))
    add_runs(p, [(f"{kind} {num}. ", {"bold": True})], size=8, color=BLUE)
    add_runs(p, inline(text), size=8)


def build(out):
    tex = strip_comments(open(SRC, encoding="utf-8").read())
    get = lambda name: group(tex, tex.index("\\" + name + "{") + len(name) + 1)[0]
    title, authors, address = get("title"), get("author"), re.search(r"\\address\[1\]\{(.*?)\}\s*(\\todo\{[^}]*\})?", tex, re.S)
    corresp, tfoot = get("corresp"), get("tfootnote")
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S).group(1)
    keywords = re.search(r"\\begin\{keywords\}(.*?)\\end\{keywords\}", tex, re.S).group(1)
    body = tex[tex.index("\\maketitle") + len("\\maketitle"):tex.index("\\begin{thebibliography}")]
    bib = re.findall(r"\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})",
                     tex[tex.index("\\begin{thebibliography}"):], re.S)
    bios = re.findall(r"\\begin\{IEEEbiographynophoto\}\{([^}]+)\}(.*?)\\end\{IEEEbiographynophoto\}", tex, re.S)

    # references in order of first citation (IEEE)
    order = []
    for m in re.finditer(r"\\cite\{([^}]+)\}", body):
        for k in m.group(1).split(","):
            if k.strip() not in order:
                order.append(k.strip())
    bib_d = dict(bib)
    order += [k for k, _ in bib if k not in order]
    CTX.cites = {k: n + 1 for n, k in enumerate(order)}

    blocks = env_blocks(body)
    n_eq = number_labels(blocks)
    assert n_eq == len(EQUATIONS), (n_eq, len(EQUATIONS))

    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(10)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(PAGE_W), Inches(11)
    sec.left_margin = sec.right_margin = Inches(MARGIN_LR)
    sec.top_margin, sec.bottom_margin = Inches(0.75), Inches(0.7)
    sec.header_distance = sec.footer_distance = Inches(0.35)

    # running head and footer
    hp = sec.header.paragraphs[0]
    add_runs(hp, [("N. K. Shahi ", {}), ("et al.", {"italic": True}),
                  (": Transaction-Bound Step-Up Authentication for High-Value Payments", {})], size=8)
    fp = sec.footer.paragraphs[0]
    fp.paragraph_format.tab_stops.add_tab_stop(Inches(PAGE_W - 2 * MARGIN_LR), WD_TAB_ALIGNMENT.RIGHT)
    add_runs(fp, [("VOLUME XX, 2026\t", {})], size=8)
    field(fp, "PAGE")

    # front matter (one column)
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT)
    add_runs(p, [("Date of publication xxxx 00, 0000, date of current version xxxx 00, 0000.", {})], size=7.5)
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT, after=10)
    add_runs(p, [("Digital Object Identifier 10.1109/ACCESS.2026.DOI", {})], size=7.5)
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT, after=10)
    add_runs(p, inline(" ".join(title.split())), size=21)
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT, after=6)
    names = re.findall(r"\\uppercase\{([^}]+)\}", authors)
    for k, n in enumerate(names):
        sep = ", " if k < len(names) - 2 else (", AND " if k == len(names) - 2 else "")
        add_runs(p, [(n.upper(), {"bold": True}), ("1", {"bold": True, "vert": "superscript"}), (sep, {"bold": True})],
                 size=10)
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT)
    add_runs(p, [("1", {"vert": "superscript"})] + inline(" ".join(address.group(1).split())
                                                          + (" " + address.group(2) if address.group(2) else "")),
             size=8)
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT, before=6)
    add_runs(p, inline(" ".join(corresp.split())), size=8)
    p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT, after=8)
    add_runs(p, inline(" ".join(tfoot.split())), size=8)

    p = para(doc, indent=0, after=2, before=4)
    add_runs(p, [("ABSTRACT ", {"bold": True})], size=9, color=BLUE)
    add_runs(p, inline(" ".join(abstract.split())), size=9)
    border(p, ("top",))
    p = para(doc, indent=0, after=10, before=4)
    add_runs(p, [("INDEX TERMS ", {"bold": True})], size=9, color=BLUE)
    add_runs(p, inline(" ".join(keywords.split())), size=9)
    border(p, ("bottom",))

    body_sec = doc.add_section(WD_SECTION.CONTINUOUS)
    set_cols(body_sec, 2)

    # body
    sec_n = subsec_n = fig_n = tab_n = eq_n = 0
    for b in blocks:
        kind = b[0]
        if kind == "section":
            sec_n, subsec_n = sec_n + 1, 0
            heading(doc, f"{ROMAN[sec_n - 1]}. {b[1]}", 1)
        elif kind == "section*":
            heading(doc, b[1], 1)
        elif kind == "subsection":
            subsec_n += 1
            heading(doc, f"{chr(64 + subsec_n)}. {b[1]}", 2)
        elif kind == "text":
            txt = b[1].strip()
            m = re.match(r"\\PARstart\{(.)\}\{([^}]*)\}", txt)
            if m:
                cap = para(doc, indent=0)
                cap.paragraph_format.line_spacing = Pt(23)
                pPr = cap._p.get_or_add_pPr()
                fr = OxmlElement("w:framePr")
                for k2, v in (("dropCap", "drop"), ("lines", "2"), ("wrap", "around"), ("vAnchor", "text"),
                              ("hAnchor", "text")):
                    fr.set(qn(f"w:{k2}"), v)
                pPr.insert(0, fr)
                add_runs(cap, [(m.group(1), {})], size=27, color=BLUE)
                p = para(doc, indent=0)
                add_runs(p, [(m.group(2).upper(), {})])
                add_runs(p, inline(txt[m.end():]))
            else:
                para(doc, txt)
        elif kind == "env":
            name, content = b[1], b[2]
            if name == "itemize":
                for item in [x.strip() for x in content.split("\\item") if x.strip()]:
                    p = para(doc, indent=0)
                    p.paragraph_format.left_indent = Inches(0.25)
                    p.paragraph_format.first_line_indent = Inches(-0.14)
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.25))
                    add_runs(p, [(BULLET, {})] + inline(item))
            elif name == "equation":
                eq_n += 1
                lines = EQUATIONS[eq_n - 1]
                lines = lines if isinstance(lines, list) else [lines]
                for k, line in enumerate(lines):
                    last = k == len(lines) - 1
                    p = para(doc, indent=0, before=3 if k == 0 else 0, after=3 if last else 1,
                             align=WD_ALIGN_PARAGRAPH.LEFT, keep=not last)
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(COL_W / 2), WD_TAB_ALIGNMENT.CENTER)
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(COL_W), WD_TAB_ALIGNMENT.RIGHT)
                    p.add_run("\t")
                    p._p.append(parse_xml(f"<m:oMath {M_NS}>{line}</m:oMath>"))
                    if last:
                        add_runs(p, [(f"\t({eq_n})", {})])
            elif name in ("figure", "figure*"):
                fig_n += 1
                img = re.search(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", content).group(1)
                cap_txt = group(content, content.index("\\caption{") + 8)[0]
                p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, keep=True)
                p.add_run().add_picture(os.path.join(HERE, img), width=Inches(COL_W))
                caption(doc, "FIGURE", fig_n, " ".join(cap_txt.split()))
            elif name == "table":
                tab_n += 1
                cap_txt = group(content, content.index("\\caption{") + 8)[0]
                caption(doc, "TABLE", tab_n, " ".join(cap_txt.split()), before=6, after=3)
                tb = content.index("\\begin{tabular}")
                spec, j = group(content, tb + len("\\begin{tabular}"))
                inner = content[j:content.index("\\end{tabular}")]
                tabular(doc, spec, inner)
                note = re.search(r"\\parbox\{\\columnwidth\}\{(.*)\}\s*$", content.strip(), re.S)
                p = para(doc, indent=0, after=8, before=2)
                if note:
                    add_runs(p, inline(" ".join(note.group(1).replace("\\footnotesize", "").split())), size=7.5)

    # references
    heading(doc, "References", 1)
    for k in order:
        p = para(doc, indent=0, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(0.3))
        add_runs(p, [(f"[{CTX.cites[k]}]\t", {})] + inline(" ".join(bib_d[k].split())), size=8)

    # biographies
    for name, text in bios:
        p = para(doc, indent=0, before=10)
        add_runs(p, [(name.upper() + " ", {"bold": True})], size=8.5, color=BLUE)
        add_runs(p, inline(" ".join(text.split())), size=8.5)

    doc.add_section(WD_SECTION.CONTINUOUS)           # balances the two columns on the last page
    doc.core_properties.title = " ".join(title.split())
    doc.core_properties.author = "VaultTrust team"
    doc.save(out)
    bib_order = [k for k, _ in bib]
    print("saved", out)
    print("references follow citation order in main.tex:", bib_order == order)
    if bib_order != order:
        print("  citation order:", order)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    target = os.path.abspath(sys.argv[1])
    if os.path.exists(target):
        sys.exit(f"{target} already exists; the hand-edited Word file is the master copy. Choose a new file name.")
    build(target)
