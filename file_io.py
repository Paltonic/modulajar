"""file_io.py — Ekstrak teks dari file PDF, DOCX, atau TXT (termasuk tabel)."""
import pypdf
from docx import Document
from docx.document import Document as _Doc
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn


def _iter_block_items(parent):
    """Iterasi elemen body (paragraph & table) sesuai urutan asli dokumen."""
    if isinstance(parent, _Doc):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        parent_elm = parent

    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def _extract_from_docx(uploaded_file):
    """Ekstrak semua teks dari DOCX termasuk seluruh isi tabel (dengan merge handling)."""
    doc = Document(uploaded_file)
    parts = []

    def process_block(block):
        if isinstance(block, Paragraph):
            t = block.text.strip()
            if t:
                parts.append(t)
        elif isinstance(block, Table):
            for row in block.rows:
                cells_text = []
                seen = set()
                for cell in row.cells:
                    key = id(cell._tc)  # dedup kolom merge (gridspan)
                    if key in seen:
                        continue
                    seen.add(key)

                    cell_parts = []
                    for sub in _iter_block_items(cell):
                        if isinstance(sub, Paragraph):
                            if sub.text.strip():
                                cell_parts.append(sub.text.strip())
                        elif isinstance(sub, Table):
                            # nested table → flatten ke baris "a | b | c"
                            for r2 in sub.rows:
                                row2 = " | ".join(
                                    c.text.strip() for c in r2.cells if c.text.strip()
                                )
                                if row2:
                                    cell_parts.append(row2)
                    joined = " ".join(cell_parts).strip()
                    if joined:
                        cells_text.append(joined)

                line = " | ".join(cells_text)
                if line:
                    parts.append(line)

    for block in _iter_block_items(doc):
        process_block(block)

    return "\n".join(parts)


def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    text = ""
    try:
        # reset pointer kalau file sudah pernah dibaca
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        name = (getattr(uploaded_file, "name", "") or "").lower()

        if name.endswith(".pdf"):
            reader = pypdf.PdfReader(uploaded_file)
            text = "\n".join((p.extract_text() or "") for p in reader.pages)

        elif name.endswith(".docx"):
            text = _extract_from_docx(uploaded_file)

        elif name.endswith(".txt"):
            raw = uploaded_file.read()
            if isinstance(raw, bytes):
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1", errors="replace")
            else:
                text = str(raw)

        else:
            return "Error: Format file tidak didukung (hanya PDF/DOCX/TXT)."

    except Exception as e:
        return f"Error membaca file: {e}"

    return text.strip()