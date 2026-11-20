"""
Small report engine on python-docx that follows the VIT Project-I template rules:
A4; margins left 1.5", others 1"; Times New Roman 12, justified, 1.5 line spacing; chapter heading
14 pt bold caps; sub-headings 12 pt; first paragraph of a chapter not indented, later ones indented;
bullet symbols (not numbering); figure captions below ("Fig. 2.4 Title"), table captions above
("Table 6.1 Title"), both TNR 10; equations numbered "(5.2)"; roman page numbers in the front
matter (hidden on the cover), arabic from Chapter 1 to References, none in the appendices.
Contents / list of figures / list of tables are Word fields, filled when Word updates the document.
"""

import copy
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

FONT = "Times New Roman"
TEXT_WIDTH = 8.27 - 1.5 - 1.0          # inches
M_NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'


def _set_font(run_or_style, size=None, bold=None, italic=None, name=FONT, color=None):
    f = run_or_style.font
    f.name = name
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color is not None:
        f.color.rgb = RGBColor.from_string(color)
    rpr = run_or_style.element.get_or_add_rPr() if hasattr(run_or_style, "element") else None
    if rpr is not None:
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.insert(0, fonts)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            fonts.set(qn(a), name)


def _field(paragraph, instr, placeholder=""):
    """Insert a complex field (TOC, PAGE, ...) into a paragraph."""
    def fc(kind):
        r = OxmlElement("w:r")
        c = OxmlElement("w:fldChar")
        c.set(qn("w:fldCharType"), kind)
        if kind == "begin":
            c.set(qn("w:dirty"), "true")
        r.append(c)
        return r
    p = paragraph._p
    p.append(fc("begin"))
    r = OxmlElement("w:r")
    t = OxmlElement("w:instrText")
    t.set(qn("xml:space"), "preserve")
    t.text = f" {instr} "
    r.append(t)
    p.append(r)
    p.append(fc("separate"))
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = placeholder
    r.append(t)
    p.append(r)
    p.append(fc("end"))


class Report:
    def __init__(self):
        self.doc = Document()
        self.chapter_no = 0
        self.sec_no = [0, 0]
        self.fig_no = self.tab_no = self.eq_no = 0
        self.first_para = True
        self.figures, self.tables = [], []
        self._setup_page(self.doc.sections[0])
        self._setup_styles()
        self._setup_numbering()
        self._num_ids = {}

    # ------------------------------------------------------------ setup
    def _setup_page(self, s):
        s.page_width, s.page_height = Inches(8.27), Inches(11.69)
        s.left_margin, s.right_margin = Inches(1.5), Inches(1.0)
        s.top_margin, s.bottom_margin = Inches(1.0), Inches(1.0)
        s.header_distance, s.footer_distance = Inches(0.5), Inches(0.5)

    def _setup_styles(self):
        st = self.doc.styles
        normal = st["Normal"]
        _set_font(normal, 12)
        pf = normal.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        pf.space_after = Pt(6)
        pf.space_before = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for name, size, caps, align in (("Heading 1", 14, True, WD_ALIGN_PARAGRAPH.CENTER),
                                        ("Heading 2", 12, False, WD_ALIGN_PARAGRAPH.LEFT),
                                        ("Heading 3", 12, False, WD_ALIGN_PARAGRAPH.LEFT)):
            h = st[name]
            _set_font(h, size, bold=True, italic=(name == "Heading 3"), color="000000")
            h.font.all_caps = caps
            hp = h.paragraph_format
            hp.alignment = align
            hp.space_before = Pt(18 if name == "Heading 1" else 12)
            hp.space_after = Pt(12 if name == "Heading 1" else 6)
            hp.keep_with_next = True
            hp.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            hp.first_line_indent = Inches(0)
            # theme fonts would override the explicit font in some Word versions
            rpr = h.element.get_or_add_rPr()
            for tag in ("w:rFonts",):
                el = rpr.find(qn(tag))
                if el is not None:
                    for a in list(el.attrib):
                        if "Theme" in a or "theme" in a.lower():
                            del el.attrib[a]
        for name, after in (("Figure Caption", 12), ("Table Caption", 4)):
            s = st.add_style(name, 1)
            s.base_style = st["Normal"]
            _set_font(s, 10, bold=False)
            s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            s.paragraph_format.space_before = Pt(4)
            s.paragraph_format.space_after = Pt(after)
            s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            s.paragraph_format.first_line_indent = Inches(0)
        s = st.add_style("Table Text", 1)
        s.base_style = st["Normal"]
        _set_font(s, 10)
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        s.paragraph_format.space_after = Pt(0)
        s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        s = st.add_style("Code", 1)
        s.base_style = st["Normal"]
        _set_font(s, 9, name="Consolas")
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        s.paragraph_format.space_after = Pt(0)
        s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        s = st.add_style("Reference", 1)
        s.base_style = st["Normal"]
        s.paragraph_format.left_indent = Inches(0.5)
        s.paragraph_format.first_line_indent = Inches(-0.5)
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        s.paragraph_format.space_after = Pt(8)
        for lvl in range(1, 4):
            try:
                t = st[f"TOC {lvl}"] if f"TOC {lvl}" in [x.name for x in st] else st.add_style(f"TOC {lvl}", 1)
            except KeyError:
                t = st.add_style(f"TOC {lvl}", 1)
            _set_font(t, 12, bold=(lvl == 1))
            t.paragraph_format.left_indent = Inches(0.3 * (lvl - 1))
            t.paragraph_format.space_after = Pt(2)
            t.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    def _setup_numbering(self):
        numbering = self.doc.part.numbering_part.element
        defs = {90: ("●", "Arial"), 91: ("✓", "Segoe UI Symbol"), 92: None}
        for aid, spec in defs.items():
            if spec:
                sym, font = spec
                lvl = (f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
                       f'<w:lvlText w:val="{sym}"/><w:lvlJc w:val="left"/>'
                       f'<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>'
                       f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:hint="default"/><w:sz w:val="18"/></w:rPr></w:lvl>')
            else:
                lvl = ('<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
                       '<w:lvlText w:val="%1."/><w:lvlJc w:val="left"/>'
                       '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl>')
            el = parse_xml(f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{aid}">'
                           f'<w:multiLevelType w:val="singleLevel"/>{lvl}</w:abstractNum>')
            first_num = numbering.find(qn("w:num"))
            if first_num is not None:
                first_num.addprevious(el)
            else:
                numbering.append(el)
        self._next_num = 900

    def _new_num(self, abstract_id):
        numbering = self.doc.part.numbering_part.element
        self._next_num += 1
        nid = self._next_num
        numbering.append(parse_xml(
            f'<w:num {nsdecls("w")} w:numId="{nid}"><w:abstractNumId w:val="{abstract_id}"/>'
            f'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'))
        return nid

    # ------------------------------------------------------------ text
    def _runs(self, par, text, size=None, bold=None, italic=None):
        """Mini markup: **bold**, *italic*, `code`, ^{sup}, _{sub}."""
        tokens = re.split(r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|\^\{[^}]+\}|_\{[^}]+\})", text)
        for tok in tokens:
            if not tok:
                continue
            b, i, code, sup, sub = bold, italic, False, False, False
            if tok.startswith("***") and tok.endswith("***") and len(tok) > 6:
                tok, b, i = tok[3:-3], True, True
            elif tok.startswith("**") and tok.endswith("**"):
                tok, b = tok[2:-2], True
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                tok, i = tok[1:-1], True
            elif tok.startswith("`") and tok.endswith("`"):
                tok, code = tok[1:-1], True
            elif tok.startswith("^{"):
                tok, sup = tok[2:-1], True
            elif tok.startswith("_{"):
                tok, sub = tok[2:-1], True
            r = par.add_run(tok)
            _set_font(r, (size or 12) - (1.5 if code else 0) if (size or code) else None, bold=b, italic=i,
                      name="Consolas" if code else FONT)
            if sup:
                r.font.superscript = True
            if sub:
                r.font.subscript = True
        return par

    def p(self, text, indent=None, align=None, size=None, bold=None, italic=None, space_after=None, keep=False):
        par = self.doc.add_paragraph()
        if indent is None:
            indent = not self.first_para
        par.paragraph_format.first_line_indent = Inches(0.5) if indent else Inches(0)
        if align == "center":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "left":
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif align == "right":
            par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if space_after is not None:
            par.paragraph_format.space_after = Pt(space_after)
        if keep:
            par.paragraph_format.keep_with_next = True
        self._runs(par, text, size, bold, italic)
        self.first_para = False
        return par

    def paras(self, text):
        for block in [b.strip() for b in text.strip().split("\n\n") if b.strip()]:
            self.p(" ".join(block.split()))

    def bullets(self, items, kind="dot"):
        nid = self._new_num(90 if kind == "dot" else 91)
        for it in items:
            par = self.doc.add_paragraph()
            ppr = par._p.get_or_add_pPr()
            ppr.append(parse_xml(f'<w:numPr {nsdecls("w")}><w:ilvl w:val="0"/><w:numId w:val="{nid}"/></w:numPr>'))
            par.paragraph_format.first_line_indent = Inches(-0.25)
            par.paragraph_format.left_indent = Inches(0.5)
            par.paragraph_format.space_after = Pt(3)
            self._runs(par, " ".join(it.split()))
        self.first_para = False

    def numbered(self, items):
        nid = self._new_num(92)
        for it in items:
            par = self.doc.add_paragraph()
            ppr = par._p.get_or_add_pPr()
            ppr.append(parse_xml(f'<w:numPr {nsdecls("w")}><w:ilvl w:val="0"/><w:numId w:val="{nid}"/></w:numPr>'))
            par.paragraph_format.first_line_indent = Inches(-0.25)
            par.paragraph_format.left_indent = Inches(0.5)
            par.paragraph_format.space_after = Pt(3)
            self._runs(par, " ".join(it.split()))
        self.first_para = False

    def code(self, text):
        lines = text.strip("\n").split("\n")
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.rows[0].cells[0]
        cell.width = Inches(TEXT_WIDTH - 0.2)
        tc_pr = cell._tc.get_or_add_tcPr()
        tc_pr.append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="F3F4F6"/>'))
        borders = parse_xml(f'<w:tcBorders {nsdecls("w")}>' + "".join(
            f'<w:{s} w:val="single" w:sz="4" w:color="BFC5CE"/>' for s in ("top", "left", "bottom", "right")) + "</w:tcBorders>")
        tc_pr.append(borders)
        first = True
        for ln in lines:
            par = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            par.style = self.doc.styles["Code"]
            r = par.add_run(ln if ln else " ")
            _set_font(r, 8.5, name="Consolas")
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # ------------------------------------------------------------ structure
    def heading1(self, text, toc=True):
        h = self.doc.add_paragraph(style="Heading 1")
        h.paragraph_format.page_break_before = True
        self._runs(h, text, size=14, bold=True)
        self.first_para = True
        return h

    def chapter(self, title):
        self.chapter_no += 1
        self.sec_no = [0, 0]
        self.fig_no = self.tab_no = self.eq_no = 0
        h = self.doc.add_paragraph(style="Heading 1")
        h.paragraph_format.page_break_before = True
        r = h.add_run(f"CHAPTER {self.chapter_no}")
        _set_font(r, 14, bold=True)
        r.add_break(WD_BREAK.LINE)
        r2 = h.add_run(title.upper())
        _set_font(r2, 14, bold=True)
        self.first_para = True

    def unnumbered_chapter(self, title):
        h = self.doc.add_paragraph(style="Heading 1")
        h.paragraph_format.page_break_before = True
        r = h.add_run(title.upper())
        _set_font(r, 14, bold=True)
        self.first_para = True

    def h2(self, title):
        self.sec_no[0] += 1
        self.sec_no[1] = 0
        h = self.doc.add_paragraph(style="Heading 2")
        r = h.add_run(f"{self.chapter_no}.{self.sec_no[0]}  {title}")
        _set_font(r, 12, bold=True)

    def h3(self, title):
        self.sec_no[1] += 1
        h = self.doc.add_paragraph(style="Heading 3")
        r = h.add_run(f"{self.chapter_no}.{self.sec_no[0]}.{self.sec_no[1]}  {title}")
        _set_font(r, 12, bold=True, italic=False)

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ------------------------------------------------------------ figures / tables / equations
    def figure(self, path, caption, width=5.6):
        self.fig_no += 1
        num = f"{self.chapter_no}.{self.fig_no}"
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.first_line_indent = Inches(0)
        par.paragraph_format.keep_with_next = True
        par.paragraph_format.space_before = Pt(6)
        par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        par.add_run().add_picture(path, width=Inches(min(width, TEXT_WIDTH)))
        cap = self.doc.add_paragraph(style="Figure Caption")
        r = cap.add_run(f"Fig. {num} {caption}")
        _set_font(r, 10)
        self.figures.append((num, caption))
        return num

    def next_fig(self):
        return f"{self.chapter_no}.{self.fig_no + 1}"

    def next_tab(self):
        return f"{self.chapter_no}.{self.tab_no + 1}"

    def table(self, caption, header, rows, widths=None, size=9.5, align=None, bold_first_col=False, highlight_rows=()):
        self.tab_no += 1
        num = f"{self.chapter_no}.{self.tab_no}"
        cap = self.doc.add_paragraph(style="Table Caption")
        cap.paragraph_format.keep_with_next = True
        r = cap.add_run(f"Table {num} {caption}")
        _set_font(r, 10)
        self.tables.append((num, caption))
        ncol = len(header)
        tbl = self.doc.add_table(rows=1, cols=ncol)
        tbl.style = self.doc.styles["Table Grid"]
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        if widths is None:
            widths = [TEXT_WIDTH / ncol] * ncol
        scale = min(1.0, TEXT_WIDTH / sum(widths))
        widths = [w * scale for w in widths]
        align = align or ["l"] * ncol

        def fill(cells, values, head=False, shade=None):
            for j, (c, v) in enumerate(zip(cells, values)):
                c.width = Inches(widths[j])
                par = c.paragraphs[0]
                par.style = self.doc.styles["Table Text"]
                par.alignment = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER,
                                 "r": WD_ALIGN_PARAGRAPH.RIGHT}[align[j] if not head else ("c" if align[j] != "l" else "l")]
                self._runs(par, str(v), size=size, bold=True if head or (bold_first_col and j == 0) else None)
                if head or shade:
                    c._tc.get_or_add_tcPr().append(parse_xml(
                        f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{"DCE3EE" if head else shade}"/>'))
        fill(tbl.rows[0].cells, header, head=True)
        trpr = tbl.rows[0]._tr.get_or_add_trPr()
        trpr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        for i, row in enumerate(rows):
            cells = tbl.add_row().cells
            fill(cells, row, shade="FFF4D6" if i in highlight_rows else None)
        for row in tbl.rows:
            row._tr.get_or_add_trPr().append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(4)
        sp.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        return num

    @staticmethod
    def _omml(parts):
        def esc(s):
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def build(x):
            if isinstance(x, str):
                return f'<m:r><m:t xml:space="preserve">{esc(x)}</m:t></m:r>'
            kind = x[0]
            if kind == "f":
                return f"<m:f><m:num>{build_all(x[1])}</m:num><m:den>{build_all(x[2])}</m:den></m:f>"
            if kind == "sub":
                return f"<m:sSub><m:e>{build_all(x[1])}</m:e><m:sub>{build_all(x[2])}</m:sub></m:sSub>"
            if kind == "sup":
                return f"<m:sSup><m:e>{build_all(x[1])}</m:e><m:sup>{build_all(x[2])}</m:sup></m:sSup>"
            if kind == "subsup":
                return (f"<m:sSubSup><m:e>{build_all(x[1])}</m:e><m:sub>{build_all(x[2])}</m:sub>"
                        f"<m:sup>{build_all(x[3])}</m:sup></m:sSubSup>")
            if kind == "sum":
                hide = ('<m:subHide m:val="1"/>' if x[1] == "" else "") + ('<m:supHide m:val="1"/>' if x[2] == "" else "")
                return (f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/>{hide}</m:naryPr>'
                        f"<m:sub>{build_all(x[1])}</m:sub><m:sup>{build_all(x[2])}</m:sup><m:e>{build_all(x[3])}</m:e></m:nary>")
            if kind == "sqrt":
                return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{build_all(x[1])}</m:e></m:rad>'
            if kind == "bar":
                return f'<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e>{build_all(x[1])}</m:e></m:bar>'
            raise ValueError(kind)

        def build_all(xs):
            if isinstance(xs, (str, tuple)):
                xs = [xs]
            return "".join(build(x) for x in xs)
        return f"<m:oMath {M_NS}>{build_all(parts)}</m:oMath>"

    def equation(self, *parts):
        self.eq_no += 1
        num = f"{self.chapter_no}.{self.eq_no}"
        par = self.doc.add_paragraph()
        par.paragraph_format.first_line_indent = Inches(0)
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        ts = par.paragraph_format.tab_stops
        ts.add_tab_stop(Inches(TEXT_WIDTH / 2), WD_TAB_ALIGNMENT.CENTER)
        ts.add_tab_stop(Inches(TEXT_WIDTH), WD_TAB_ALIGNMENT.RIGHT)
        par.add_run("\t")
        par._p.append(parse_xml(self._omml(list(parts))))
        r = par.add_run(f"\t({num})")
        _set_font(r, 12)
        return num

    # ------------------------------------------------------------ lists of contents (Word fields)
    def toc(self):
        par = self.doc.add_paragraph()
        _field(par, 'TOC \\o "1-2" \\h \\z \\u', "Right-click and choose Update Field to build the contents.")

    def list_of(self, style):
        par = self.doc.add_paragraph()
        _field(par, f'TOC \\h \\z \\t "{style},1"', "Update field to build this list.")

    # ------------------------------------------------------------ sections and page numbers
    def _footer_page(self, section, fmt, start, number=True, title_page=False):
        sp = section._sectPr
        for old in sp.findall(qn("w:pgNumType")):
            sp.remove(old)
        if fmt:
            pg = OxmlElement("w:pgNumType")
            pg.set(qn("w:fmt"), fmt)
            pg.set(qn("w:start"), str(start))
            sp.append(pg)
        section.different_first_page_header_footer = title_page
        footer = section.footer
        footer.is_linked_to_previous = False
        par = footer.paragraphs[0]
        for r in list(par.runs):
            r._r.getparent().remove(r._r)
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if number:
            _field(par, "PAGE", "1")
            for r in par._p.findall(qn("w:r")):
                rpr = OxmlElement("w:rPr")
                fonts = OxmlElement("w:rFonts")
                for a in ("w:ascii", "w:hAnsi", "w:cs"):
                    fonts.set(qn(a), FONT)
                rpr.append(fonts)
                sz = OxmlElement("w:sz")
                sz.set(qn("w:val"), "22")
                rpr.append(sz)
                r.insert(0, rpr)
        if title_page:
            fp = section.first_page_footer
            fp.is_linked_to_previous = False

    def front_matter_numbering(self):
        self._footer_page(self.doc.sections[0], "lowerRoman", 1, True, title_page=True)

    def new_section(self, kind):
        """kind: 'main' (arabic from 1) or 'appendix' (no page numbers)."""
        s = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self._setup_page(s)
        if kind == "main":
            self._footer_page(s, "decimal", 1, True)
        else:
            self._footer_page(s, None, 1, False)
        self.first_para = True
        return s

    def save(self, path):
        # ask Word to refresh fields (TOC, lists, page numbers) when the file is opened
        settings = self.doc.settings.element
        upd = settings.find(qn("w:updateFields"))
        if upd is None:
            upd = OxmlElement("w:updateFields")
            settings.append(upd)
        upd.set(qn("w:val"), "true")
        self.doc.save(path)
