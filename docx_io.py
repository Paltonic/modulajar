"""docx_io.py — Export Modul Ajar (Cambridge English)."""
import os
import re
from io import BytesIO
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

JP_FONT = "Yu Gothic"
HEADER_FILL = "D9E1F2"

# Cari logo di folder yang sama dengan file ini
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo_nakamura.png")


# =========================================================
# Low-level helpers
# =========================================================
def _set_cjk(run, font=JP_FONT, size=12):
    run.font.name = "Arial"
    run.font.size = Pt(size)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), font)

def _shade_cell(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color_hex)
    tcPr.append(shd)

def _write_cell(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, size=12):
    cell.text = ""
    text = str(text) if text is not None else ""

    # Memisahkan penomoran 1. 2. 3. yang menyatu menjadi enter di Word
    text = re.sub(r'(?<!\n)\s*(\d+)[\.\)]\s+', r'\n\1. ', text).strip()

    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(line)
        r.bold = bold
        r.font.name = "Arial"
        r.font.size = Pt(size)
        if any(ord(c) > 0x3000 for c in line):
            _set_cjk(r, size=size)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

def _bullets_from_list(items):
    if not items: return "-"
    return "\n".join(f"- {x}" for x in items)

def _numbered_from_list(items):
    if not items: return "-"
    return "\n".join(f"{i + 1}. {x}" for i, x in enumerate(items))

def _remove_table_borders(table):
    """Hilangkan semua border (untuk header logo + judul)."""
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"), "none")
        border.set(qn("w:sz"), "0")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "auto")
        borders.append(border)
    tblPr.append(borders)


# =========================================================
# Main exporter
# =========================================================
def export_docx(data, info, logo_path=None):
    doc = Document()

    # ---------- Set Default Font to Arial 12 ----------
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(12)

    # ---------- Page setup: LANDSCAPE ----------
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    new_w, new_h = section.page_height, section.page_width
    section.page_width  = new_w
    section.page_height = new_h
    section.top_margin    = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin   = Cm(1.5)
    section.right_margin  = Cm(1.5)

    # ---------- Header: Logo + Judul (sejajar) ----------
    year = info.get("academic_year", "2026/2027")
    jenjang = info.get("jenjang", "SMA")
    title_text = f"Modul Ajar Academic Year {year} {jenjang} Swasta Nakamura School"

    logo_file = logo_path or LOGO_PATH
    header_tbl = doc.add_table(rows=1, cols=2)
    header_tbl.autofit = False
    header_tbl.allow_autofit = False
    _remove_table_borders(header_tbl)

    # Kunci layout tabel header
    tblPr_h = header_tbl._tbl.tblPr
    layout_h = OxmlElement('w:tblLayout')
    layout_h.set(qn('w:type'), 'fixed')
    tblPr_h.append(layout_h)

    # Kiri: logo (Lebar: 4.5 cm)
    logo_cell = header_tbl.cell(0, 0)
    logo_cell.width = Cm(4.5)
    if os.path.exists(logo_file):
        try:
            p = logo_cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run()
            run.add_picture(logo_file, width=Cm(3.5))
        except Exception:
            logo_cell.text = "[LOGO]"
    else:
        logo_cell.text = "[LOGO NAKAMURA]"

    # Kanan: judul (Lebar: 20.5 cm)
    title_cell = header_tbl.cell(0, 1)
    title_cell.width = Cm(20.5)
    p = title_cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(title_text)
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(24)
    
    # Terapkan lebar ke kedua sel agar proporsional (1:4.5)
    header_tbl.columns[0].width = Cm(4.5)
    header_tbl.columns[1].width = Cm(20.5)
    header_tbl.cell(0, 0).width = Cm(4.5)
    header_tbl.cell(0, 1).width = Cm(20.5)

    doc.add_paragraph()

    # ---------- Info table 1 ----------
    t1 = doc.add_table(rows=2, cols=4)
    t1.style = "Table Grid"
    headers1 = ["Teacher's Name", "Subject", "Time & Duration", "Unit / Elemen"]
    values1 = [
        info.get("teacher", "-"),
        info.get("subject", "-"),
        info.get("duration", "-"),
        info.get("unit_elemen", "-"),
    ]
    for i in range(4):
        _write_cell(t1.cell(0, i), headers1[i], bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _shade_cell(t1.cell(0, i), HEADER_FILL)
        _write_cell(t1.cell(1, i), values1[i], align=WD_ALIGN_PARAGRAPH.CENTER)
    for row in t1.rows:
        for i, w in enumerate([Cm(6.5), Cm(6), Cm(6), Cm(6.5)]):
            row.cells[i].width = w

    # ---------- Info table 2 ----------
    t2 = doc.add_table(rows=2, cols=4)
    t2.style = "Table Grid"
    headers2 = ["Term/SMT", "Class", "Phase", "Assessment"]
    values2 = [info.get("term", "-"), info.get("class_level", "-"), info.get("phase", "-"), "-"]
    for i in range(4):
        _write_cell(t2.cell(0, i), headers2[i], bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _shade_cell(t2.cell(0, i), HEADER_FILL)
        _write_cell(t2.cell(1, i), values2[i], align=WD_ALIGN_PARAGRAPH.CENTER)
    for row in t2.rows:
        for i, w in enumerate([Cm(6.5), Cm(6), Cm(6), Cm(6.5)]):
            row.cells[i].width = w

    doc.add_paragraph()

    # ---------- Content table: CP / PK / GQ / EU / KV / RM ----------
    pk_header = (
        "Prior Knowledge\n"
        "(What have learners already covered or what do they need to know in order "
        "to access this lesson? How will they check their previous learning?)"
    )

    kv_items = data.get("key_vocabulary", []) or []
    kv_text = "\n".join(
        f"- {v.get('jp', '')}  ({v.get('romaji', '')})  —  {v.get('arti', '')}"
        for v in kv_items
    ) or "-"

    cp_text = data.get("learning_outcomes") or "(Kosong — silakan copy Capaian Pembelajaran dari website pemerintah)"

    content_rows = [
        ("Learning Outcomes", cp_text),
        (pk_header, _bullets_from_list(data.get("prior_knowledge"))),
        ("Guiding/Essential Questions", _numbered_from_list(data.get("guiding_questions"))),
        ("Enduring Understanding", data.get("enduring_understanding", "-") or "-"),
        ("Key Vocabulary", kv_text),
        ("Resources & Materials", _bullets_from_list(data.get("resources_materials"))),
    ]

    t3 = doc.add_table(rows=len(content_rows), cols=2)
    t3.style = "Table Grid"
    t3.autofit = False
    t3.allow_autofit = False

    for i, (label, content) in enumerate(content_rows):
        _write_cell(t3.cell(i, 0), label, bold=True)
        _shade_cell(t3.cell(i, 0), HEADER_FILL)
        is_cp_row = ("learning outcomes" in label.lower()) or ("capaian pembelajaran" in label.lower())
        align = WD_ALIGN_PARAGRAPH.JUSTIFY if is_cp_row else WD_ALIGN_PARAGRAPH.LEFT
        _write_cell(t3.cell(i, 1), content, align=align)
        
    # Kunci tabel agar pas 100% lebar halaman (TIDAK GESER KE KANAN)
    tblPr = t3._tbl.tblPr
    tblW = OxmlElement('w:tblW')
    tblW.set(qn('w:w'), '5000')
    tblW.set(qn('w:type'), 'pct')
    tblPr.append(tblW)
    
    layout = OxmlElement('w:tblLayout')
    layout.set(qn('w:type'), 'fixed')
    tblPr.append(layout)
    
    # Terapkan rasio 1 : 3 (6.5 cm : 19.5 cm)
    t3.columns[0].width = Cm(6)
    t3.columns[1].width = Cm(19)
    
    for row in t3.rows:
        row.cells[0].width = Cm(6)
        row.cells[1].width = Cm(19)

    doc.add_paragraph()

    # ---------- Subject Integration table ----------
    si = data.get("subject_integration") or {}
    si_subjects = si.get("subjects") or [] if isinstance(si, dict) else []
    if si_subjects:
        t_si = doc.add_table(rows=1, cols=3)
        t_si.style = "Table Grid"
        hdr = ["Integrated Subject", "Connection to the Topic", "Daily Life Implementation"]
        for i, h in enumerate(hdr):
            _write_cell(t_si.cell(0, i), h, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            _shade_cell(t_si.cell(0, i), HEADER_FILL)
        for s in si_subjects:
            cells = t_si.add_row().cells
            _write_cell(cells[0], s.get("subject", "-"))
            _write_cell(cells[1], s.get("connection", "-"))
            _write_cell(cells[2], s.get("daily_life", "-"))
        for row in t_si.rows:
            row.cells[0].width = Cm(5)
            row.cells[1].width = Cm(10.5)
            row.cells[2].width = Cm(10)
        doc.add_paragraph()

    # ---------- Character Building table ----------
    t4 = doc.add_table(rows=1, cols=2)
    t4.style = "Table Grid"
    _write_cell(t4.cell(0, 0), "Dimensi Profil Lulusan", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _write_cell(t4.cell(0, 1), "Keterangan", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _shade_cell(t4.cell(0, 0), HEADER_FILL)
    _shade_cell(t4.cell(0, 1), HEADER_FILL)
    for k, v in (data.get("character_building", {}) or {}).items():
        row = t4.add_row().cells
        _write_cell(row[0], k)
        _write_cell(row[1], v)
    for row in t4.rows:
        row.cells[0].width = Cm(6)
        row.cells[1].width = Cm(19.5)

    doc.add_paragraph()

    # ---------- Learning Objectives section ----------
    p = doc.add_paragraph()
    r = p.add_run("Learning Objective")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(12)

    doc.add_paragraph()

    for m in data.get("meetings", []):
        p = doc.add_paragraph()
        r = p.add_run(f"Meeting {m['number']}:")
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(12)

        objs = m.get("objectives") or ["-"]
        while len(objs) < 3:
            objs.append("-")
        for obj in objs:
            bp = doc.add_paragraph(style="List Bullet")
            br = bp.add_run(str(obj))
            br.font.name = "Arial"
            br.font.size = Pt(12)
        doc.add_paragraph()

    # ---------- 5E / 6-Stage table per meeting ----------
    stage_desc = {
        "Tuning In":          "Spark curiosity and connect to prior knowledge.",
        "Finding Out":        "Gathering new information from different sources.",
        "Sorting Out":        "Organising and making sense of the information collected.",
        "Going Further":      "Deepening the inquiry by exploring new questions.",
        "Making Conclusions": "Synthesising understanding, forming opinions, and making meaning.",
        "Taking Actions":     "Applying new knowledge in meaningful ways.",
    }

    for m in data.get("meetings", []):
        stages_dict = {s["stage"]: s for s in m.get("stages", [])}

        table = doc.add_table(rows=9, cols=4)
        table.style = "Table Grid"
        widths = [Cm(5), Cm(5.5), Cm(10.5), Cm(4.5)]
        for i, w in enumerate(widths):
            for row in table.rows:
                row.cells[i].width = w

        headers = [
            "Students Experience Model Steps",
            "Inquiry Cycle Steps",
            "Planned Activities",
            "Integrated Values & Skills",
        ]
        for i, h in enumerate(headers):
            _write_cell(table.cell(0, i), h, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            _shade_cell(table.cell(0, i), HEADER_FILL)

        cell_title = table.cell(1, 0).merge(table.cell(1, 3))
        meeting_title = f"Meeting {m['number']} ({m.get('day_date', 'TBD')})"
        _write_cell(cell_title, meeting_title, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

        # Understanding block (rows 2-4)
        cell_und = table.cell(2, 0).merge(table.cell(4, 0))
        _write_cell(cell_und, "Understanding\n(Memahami)", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        for idx, stage_name in enumerate(["Tuning In", "Finding Out", "Sorting Out"]):
            row_idx = 2 + idx
            sd = stages_dict.get(stage_name, {"activity": "-", "values": "-"})
            _write_cell(table.cell(row_idx, 1), f"{stage_name}\n{stage_desc[stage_name]}")
            _write_cell(table.cell(row_idx, 2), sd.get("activity", "-"))
            _write_cell(table.cell(row_idx, 3), sd.get("values", "-"))

        # Application block (rows 5-7)
        cell_app = table.cell(5, 0).merge(table.cell(7, 0))
        _write_cell(cell_app, "Application\n(Aplikasi)", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        for idx, stage_name in enumerate(["Going Further", "Making Conclusions", "Taking Actions"]):
            row_idx = 5 + idx
            sd = stages_dict.get(stage_name, {"activity": "-", "values": "-"})
            _write_cell(table.cell(row_idx, 1), f"{stage_name}\n{stage_desc[stage_name]}")
            _write_cell(table.cell(row_idx, 2), sd.get("activity", "-"))
            _write_cell(table.cell(row_idx, 3), sd.get("values", "-"))

        # Assessment row (row 8)
        _write_cell(table.cell(8, 0), "Assessment & Reflection", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _write_cell(table.cell(8, 1), "Assessment and Student Reflection")
        cell_assess = table.cell(8, 2).merge(table.cell(8, 3))
        _write_cell(cell_assess, data.get("assessment_reflection", "-") or "-")

        doc.add_paragraph()

    # ---------- Note ----------
    p = doc.add_paragraph()
    r = p.add_run("Note:")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(12)

    for note in [
        "Please attach all teaching materials used during this week's lesson, such as "
        "worksheets, presentation slides (PPT), assessment rubrics, learning media, or "
        "any other supporting documents.",
        "If any teaching materials are not yet completed or cannot be attached this week, "
        "please complete and submit them together with the lesson plan documentation in "
        "the following week.",
    ]:
        bp = doc.add_paragraph(style="List Bullet")
        br = bp.add_run(note)
        br.font.name = "Arial"
        br.font.size = Pt(12)

    # ---------- Signatures ----------
    doc.add_paragraph()
    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_date = p_date.add_run(f"{info.get('place', 'Medan')}, {info.get('date', '')}")
    run_date.font.name = "Arial"
    run_date.font.size = Pt(12)

    sig = doc.add_table(rows=2, cols=3)
    labels = ["Prepared by", "Reviewed by", "Approved by"]
    names = [info.get("teacher", "-"), info.get("reviewer", "-"), info.get("approver", "-")]
    for i in range(3):
        sig.rows[0].cells[i].text = ""
        p = sig.rows[0].cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(labels[i])
        r.font.name = "Arial"
        r.font.size = Pt(12)

        sig.rows[1].cells[i].text = ""
        p2 = sig.rows[1].cells[i].paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run("\n\n\n" + names[i])
        r2.font.name = "Arial"
        r2.font.size = Pt(12)
        r2.bold = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()