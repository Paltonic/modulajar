"""app.py — Streamlit UI: Modul Ajar Generator (No-API, Paste-to-Claude).

Flow:
  STEP 1: Build modul prompt (CP otomatis dari CP_GRAPH)
  STEP 2: Copy modul prompt ke Claude
  STEP 3: Paste modul JSON -> preview -> export DOCX

Output modul: Cambridge English (British English).
"""
import datetime
import json
import re
import pandas as pd
import streamlit as st

from ai_modul import (
    build_modul_prompt,
    _normalize, _parse_json,
    BLOOM_LEVELS, SUBJECTS, get_cp,
)
from docx_io import export_docx
from file_io import extract_text_from_file

st.set_page_config(page_title="Modul Ajar Generator", page_icon="📚", layout="wide")


# =========================================================
# Helper tanggal
# =========================================================
DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]


def format_date_en(d):
    if isinstance(d, datetime.date):
        return f"{DAYS_EN[d.weekday()]}, {d.day} {MONTHS_EN[d.month-1]} {d.year}"
    return str(d) if d else ""


# =========================================================
# Mapping Kelas → Fase (single source of truth)
# =========================================================
CLASS_LEVEL_OPTIONS = [
    "K1", "K2",          # Fase A (SD 1-2)
    "K3", "K4",          # Fase B (SD 3-4)
    "P5", "P6",          # Fase C (SD 5-6)
    "J1", "J2", "J3",    # Fase D (SMP 7-9)
    "S1",                # Fase E (SMA/SMK 10)
    "S2", "S3",          # Fase F (SMA/SMK 11-12)
]

PHASE_MAP = {
    "K1": "A", "K2": "A",
    "K3": "B", "K4": "B",
    "P5": "C", "P6": "C",
    "J1": "D", "J2": "D", "J3": "D",
    "S1": "E",
    "S2": "F", "S3": "F",
}


# =========================================================
# State initialization
# =========================================================
if "modul" not in st.session_state:
    st.session_state["modul"] = None
if "modul_info" not in st.session_state:
    st.session_state["modul_info"] = {}
if "prompt_ready" not in st.session_state:
    st.session_state["prompt_ready"] = None
if "cp_list" not in st.session_state:
    st.session_state["cp_list"] = []
if "meetings_list" not in st.session_state:
    st.session_state["meetings_list"] = [{
        "number": 1, "topic": "", "level": "Memahami",
        "date_obj": datetime.date.today(),
        "date": format_date_en(datetime.date.today()),
    }]


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("📄 1. Upload Referensi (Opsional)")
st.sidebar.caption("Upload Silabus/ATP untuk memperkaya prompt modul.")

uploaded_doc = st.sidebar.file_uploader(
    "Pilih file (PDF/DOCX/TXT)",
    type=["pdf", "docx", "txt"],
    label_visibility="collapsed",
)

ref_text = ""
if uploaded_doc:
    ref_text = extract_text_from_file(uploaded_doc)
    if ref_text and not ref_text.startswith("Error"):
        st.sidebar.success(f"Berhasil membaca dokumen ({len(ref_text)} karakter).")
    else:
        st.sidebar.error("Gagal membaca file.")

st.sidebar.divider()
st.sidebar.title("🏫 2. Identitas Modul")
teacher = st.sidebar.text_input("Nama Guru", value="Frederick Liko, S.Kom.", key="in_teacher")

subject = st.sidebar.selectbox(
    "Mata Pelajaran",
    SUBJECTS,
    index=0,
    key="in_subject_sel",
)

jenjang = st.sidebar.selectbox(
    "Jenjang Pendidikan (Untuk Judul)",
    ["TK", "SD", "SMP", "SMA", "SMK"],
    index=3, key="in_jenjang",
)

class_level = st.sidebar.selectbox(
    "Kelas (Untuk Kolom Tabel)",
    CLASS_LEVEL_OPTIONS,
    index=CLASS_LEVEL_OPTIONS.index("S2"),
    key="in_class",
)
phase = PHASE_MAP.get(class_level, "F")
st.sidebar.text_input("Fase (otomatis dari Kelas)", value=phase, disabled=True, key="in_phase_display")

duration = st.sidebar.text_input("Durasi per Meeting", value="2 x 40 menit", key="in_dur")
term = st.sidebar.text_input("Term / Semester", value="1/1", key="in_term")
academic_year = st.sidebar.text_input("Tahun Ajaran", value="2026/2027", key="in_year")
unit_elemen = st.sidebar.text_input("Unit / Elemen", value="AI Development", key="in_unit")

st.sidebar.divider()
st.sidebar.title("✍️ 3. Tanda Tangan")

DEFAULT_REVIEWER = "Aldi Permana Sembiring, S.Pd., B.Ed., Gr"

REVIEWER_MAP = {
    "SD": "Mei Nila Lipina Sinaga, S.Pd., B.Ed., Gr",
}

APPROVER_MAP = {
    "TK":  "Yuniarti Kristiany, S.Pd., B.SC., Gr",
    "SD":  "Yuniarti Kristiany, S.Pd., B.SC., Gr",
    "SMP": "Gabriel Joshua Bastiaans, S.Pd., B.Ed., Gr",
    "SMA": "Sri Hartati Siahaan, S.TP., M.Pd., Gr",
    "SMK": "Sri Hartati Siahaan, S.TP., M.Pd., Gr",
}

if st.session_state.get("_prev_jenjang") != jenjang:
    st.session_state["_prev_jenjang"] = jenjang
    st.session_state["in_reviewer"] = REVIEWER_MAP.get(jenjang, DEFAULT_REVIEWER)
    st.session_state["in_approver"] = APPROVER_MAP.get(
        jenjang, "Gabriel Joshua Bastiaans, S.Pd."
    )

reviewer = st.sidebar.text_input("Reviewed by", key="in_reviewer")
approver = st.sidebar.text_input("Approved by", key="in_approver")
place = st.sidebar.text_input("Kota", value="Medan")

st.sidebar.divider()
st.sidebar.info(
    "ℹ️ **Mode No-API**\n\n"
    "Prompt dibangun **lokal**, Anda paste ke **Claude.ai**, "
    "lalu paste JSON balik ke app ini untuk **export DOCX**.\n\n"
    "CP otomatis dimuat dari **CP_GRAPH** berdasarkan Kelas + Subject.\n\n"
    "🇬🇧 **Output modul dalam Cambridge English (British English).**\n\n"
    "Tidak ada API key, tidak ada biaya otomatis."
)


# =========================================================
# HALAMAN UTAMA — Dynamic Meetings
# =========================================================
st.title("📚 Modul Ajar Generator")
st.markdown(
    "**Flow:** STEP 1 (build prompt modul) → STEP 2 (copy ke Claude) → "
    "STEP 3 (paste JSON balik) → Export DOCX. "
    "CP otomatis dimuat dari **CP_GRAPH**. "
    "**Output modul dalam Cambridge English.**"
)

for i, m in enumerate(st.session_state["meetings_list"]):
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 1.5, 2, 0.5])
        m["topic"] = c1.text_input(
            f"Topik Meeting {m['number']}",
            value=m["topic"], key=f"topic_{i}",
        )
        m["level"] = c2.selectbox(
            f"Level Kognitif {m['number']}",
            BLOOM_LEVELS,
            index=BLOOM_LEVELS.index(m["level"]),
            key=f"level_{i}",
        )
        default_date = m.get("date_obj") or datetime.date.today()
        date_val = c3.date_input(f"Tanggal M{m['number']}", value=default_date, key=f"date_{i}")
        m["date_obj"] = date_val
        m["date"] = format_date_en(date_val)

        if len(st.session_state["meetings_list"]) > 1:
            if c4.button("🗑️", key=f"del_{i}", help="Hapus meeting ini"):
                st.session_state["meetings_list"].pop(i)
                for j, x in enumerate(st.session_state["meetings_list"]):
                    x["number"] = j + 1
                st.rerun()

st.write("")
if st.button("➕ Tambah Meeting", use_container_width=True):
    st.session_state["meetings_list"].append({
        "number": len(st.session_state["meetings_list"]) + 1,
        "topic": "", "level": "Memahami",
        "date_obj": datetime.date.today(),
        "date": format_date_en(datetime.date.today()),
    })
    st.rerun()

st.divider()


# =========================================================
# AUTO-LOAD CP (silent) dari CP_GRAPH
# =========================================================
cp_key = (
    str(phase).strip().upper(),
    str(class_level).strip().upper(),
    str(subject).strip(),
)
if st.session_state.get("_cp_key") != cp_key:
    st.session_state["_cp_key"] = cp_key
    st.session_state["cp_list"] = get_cp(phase, class_level, subject)
    # Force reset e_lo (Preview LO) agar sinkron saat kelas diganti
    st.session_state.pop("e_lo", None)

cp_current = st.session_state.get("cp_list", [])
with st.expander(
    f"🎯 Capaian Pembelajaran — {len(cp_current)} item "
    f"(Fase {phase} · {class_level} · {subject}) — klik untuk lihat/edit",
    expanded=False,
):
    if cp_current:
        st.caption(
            f"CP dimuat otomatis dari `CP_GRAPH` untuk "
            f"Fase **{phase}** / Kelas **{class_level}** / **{subject}**. "
            "Bisa diedit di bawah (satu CP per baris)."
        )
    else:
        st.caption(
            f"CP untuk Fase **{phase}** / Kelas **{class_level}** / **{subject}** "
            "masih kosong. Silakan isi manual di bawah, "
            "atau tambahkan di `CP_GRAPH` pada `ai_modul.py`."
        )

    cp_text_current = "\n".join(cp_current)
    
    # DYNAMIC KEY: Memaksa text area refresh saat kelas/mapel berubah
    dynamic_cp_key = f"cp_edit_box_{phase}_{class_level}_{subject.replace(' ', '_')}"
    
    edited_cp = st.text_area(
        "Satu CP per baris. Kosongkan baris yang tidak dipakai.",
        value=cp_text_current, height=200, key=dynamic_cp_key,
        label_visibility="collapsed",
    )
    new_cp_list = [line.strip() for line in edited_cp.split("\n") if line.strip()]
    
    if new_cp_list != cp_current:
        st.session_state["cp_list"] = new_cp_list
        # Sinkronkan langsung ke Preview LO di bawah jika ada perubahan
        if "e_lo" in st.session_state:
            st.session_state["e_lo"] = "\n".join(f"{i+1}. {cp}" for i, cp in enumerate(new_cp_list))

    st.caption(f"ℹ️ {len(new_cp_list)} CP aktif.")


# =========================================================
# STEP 1 — Build modul prompt
# =========================================================
st.header("📝 STEP 1 — Build Prompt Modul Ajar")

if st.button("🚀 Build Prompt Modul", type="primary", use_container_width=True):
    empty_topics = [m["number"] for m in st.session_state["meetings_list"] if not m["topic"].strip()]
    if empty_topics:
        st.error(f"Topik Meeting {', '.join(map(str, empty_topics))} masih kosong!")
    else:
        if not st.session_state.get("cp_list"):
            st.warning("⚠️ Belum ada CP. Modul tetap bisa di-generate, tapi lebih baik isi CP dulu.")
        try:
            # Prioritas: Ambil dari kotak Preview (e_lo) jika user sudah mengeditnya
            if "e_lo" in st.session_state and st.session_state["e_lo"].strip():
                lo_lines = st.session_state["e_lo"].split("\n")
                # Bersihkan penomoran manual agar tidak dobel "1. 1. ..."
                clean_cp = [re.sub(r'^\d+\.\s*', '', line.strip()) for line in lo_lines if line.strip()]
                cp_to_use = clean_cp
            else:
                cp_to_use = st.session_state.get("cp_list", [])

            prompt = build_modul_prompt(
                teacher=teacher, subject=subject, class_level=class_level,
                phase=phase, duration=duration, term=term,
                meetings=st.session_state["meetings_list"],
                reference_text=ref_text,
                cp_list=cp_to_use, # Menggunakan CP yang sudah disinkronkan
            )
            st.session_state["prompt_ready"] = prompt
            st.session_state["modul_info"] = {
                "teacher": teacher, "subject": subject,
                "class_level": class_level, "jenjang": jenjang,
                "phase": phase, "duration": duration, "term": term,
                "reviewer": reviewer, "approver": approver,
                "place": place, "date": format_date_en(datetime.date.today()),
                "academic_year": academic_year,
                "topic": f"{len(st.session_state['meetings_list'])} Meetings",
                "unit_elemen": unit_elemen,
            }
            st.success("✅ Modul prompt siap. Lanjut ke STEP 2.")
        except Exception as e:
            st.error(f"Gagal build prompt: {e}")


# =========================================================
# STEP 2 — Display modul prompt
# =========================================================
if st.session_state.get("prompt_ready"):
    st.divider()
    st.header("📋 STEP 2 — Copy Modul Prompt ke Claude.ai")
    st.info(
        "1. Klik **Copy** di pojok kanan atas kotak hitam\n"
        "2. Paste ke [claude.ai](https://claude.ai)\n"
        "3. Tunggu selesai (30–120 detik, tergantung jumlah meeting)\n"
        "4. **Ctrl+A → Ctrl+C** untuk copy seluruh jawaban Claude\n"
        "5. Lanjut ke STEP 3\n\n"
        "🇬🇧 **Output modul akan dihasilkan dalam Cambridge English (British English).**"
    )
    st.code(st.session_state["prompt_ready"], language="text")
    st.download_button(
        "⬇️ Download Modul Prompt (.txt)",
        data=st.session_state["prompt_ready"],
        file_name="prompt_modul.txt",
        mime="text/plain",
        use_container_width=True,
    )


# =========================================================
# STEP 3 — Paste modul JSON
# =========================================================
if st.session_state.get("prompt_ready"):
    st.divider()
    st.header("📥 STEP 3 — Paste Jawaban Modul (JSON)")

    pasted = st.text_area(
        "Paste seluruh respons Claude di sini (boleh termasuk ```json ... ```):",
        height=320, key="pasted_json",
        placeholder='{"learning_outcomes": "", "prior_knowledge": [...], ...}',
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("🔍 Parse & Preview Modul", type="primary", use_container_width=True):
            if not pasted or not pasted.strip():
                st.error("Kotak paste masih kosong.")
            else:
                try:
                    parsed = _parse_json(pasted)
                    normalized = _normalize(parsed, st.session_state["meetings_list"])

                    cp_list = st.session_state.get("cp_list", [])
                    if cp_list:
                        normalized["learning_outcomes"] = "\n".join(
                            f"{i+1}. {cp}" for i, cp in enumerate(cp_list)
                        )

                    st.session_state["modul"] = normalized
                    # Hapus e_lo agar Preview mengambil data murni dari JSON baru
                    st.session_state.pop("e_lo", None) 
                    st.success(f"✅ Berhasil parse — {len(normalized['meetings'])} meeting, {len(cp_list)} CP.")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(
                        f"❌ JSON tidak valid: {e}\n\n"
                        "Kemungkinan: jawaban terpotong / copy tidak lengkap / "
                        "ada teks di luar JSON."
                    )
                except Exception as e:
                    st.error(f"❌ Gagal parse: {e}")
    with c2:
        if st.button("🧹 Reset Prompt", use_container_width=True):
            st.session_state.pop("prompt_ready", None)
            st.session_state.pop("pasted_json", None)
            st.rerun()


# =========================================================
# RENDER HASIL MODUL
# =========================================================
data = st.session_state["modul"]
info = st.session_state["modul_info"]

if data:
    st.divider()
    st.subheader(f"✏️ Preview Modul ({info.get('topic', '')})")

    def collect():
        def get(key, default):
            return st.session_state.get(key, default)

        kv_edited = get("e_kv", None)
        kv = kv_edited.to_dict("records") if isinstance(kv_edited, pd.DataFrame) else data["key_vocabulary"]

        cb_edited = get("e_cb", None)
        cb = (
            {row["Dimensi"]: row["Deskripsi"] for _, row in cb_edited.iterrows()}
            if isinstance(cb_edited, pd.DataFrame)
            else data["character_building"]
        )

        si_edited = get("e_si", None)
        if isinstance(si_edited, pd.DataFrame):
            si_subjects = si_edited.to_dict("records")
        else:
            si_subjects = (data.get("subject_integration") or {}).get("subjects", [])

        meetings = []
        for i, m in enumerate(data["meetings"]):
            edited = get(f"e_meet_{i}", None)
            stages = edited.to_dict("records") if isinstance(edited, pd.DataFrame) else m["stages"]

            obj_list = st.session_state.get(f"list_obj_{i}", m.get("objectives", []))
            objs = [str(o).strip() for o in obj_list if str(o).strip() and o != "-"]
            if not objs:
                objs = ["-"]

            ar_val = st.session_state.get(f"e_ar_{i}", m.get("assessment_reflection", ""))

            meetings.append({
                **m, 
                "stages": stages, 
                "objectives": objs, 
                "assessment_reflection": ar_val
            })

        lo_edited = get("e_lo", data["learning_outcomes"])

        return {
            "learning_outcomes": lo_edited,
            "prior_knowledge": [get(f"e_pk_{i}", x) for i, x in enumerate(data["prior_knowledge"])],
            "guiding_questions": [get(f"e_gq_{i}", x) for i, x in enumerate(data["guiding_questions"])],
            "enduring_understanding": get("e_eu", data["enduring_understanding"]),
            "key_vocabulary": kv,
            "resources_materials": [get(f"e_rm_{i}", x) for i, x in enumerate(data["resources_materials"])],
            "subject_integration": {"subjects": si_subjects},
            "character_building": cb,
            "meetings": meetings,
            "assessment_reflection": get("e_ar_global", data.get("assessment_reflection", "-")),
        }

    tab1, tab2, tab3 = st.tabs(["📋 Tujuan & Konteks", "📖 Vocab & Karakter", "🔄 Inquiring Cycle"])

    with tab1:
        st.text_area(
            "Capaian Pembelajaran (dari CP_GRAPH, bisa diedit)",
            value=data["learning_outcomes"], height=180, key="e_lo",
        )
        st.markdown("**Prior Knowledge**")
        for i, x in enumerate(data["prior_knowledge"]):
            st.text_input(f"PK {i+1}", value=x, key=f"e_pk_{i}")
        st.markdown("**Guiding Questions**")
        for i, x in enumerate(data["guiding_questions"]):
            st.text_input(f"GQ {i+1}", value=x, key=f"e_gq_{i}")
        st.text_area("Enduring Understanding", value=data["enduring_understanding"], key="e_eu")

    with tab2:
        st.markdown("**Key Vocabulary**")
        kv_df = pd.DataFrame(data["key_vocabulary"] or [{"jp": "", "romaji": "", "arti": ""}])
        st.data_editor(kv_df, num_rows="dynamic", use_container_width=True, key="e_kv", hide_index=True)

        st.markdown("**Resources**")
        for i, x in enumerate(data["resources_materials"]):
            st.text_input(f"Resource {i+1}", value=x, key=f"e_rm_{i}")

        st.markdown("**Subject Integration & Daily Life Implementation**")
        si_subjects = (data.get("subject_integration") or {}).get("subjects", [])
        si_df = pd.DataFrame(si_subjects) if si_subjects else pd.DataFrame(
            [{"subject": "", "connection": "", "daily_life": ""}]
        )
        st.data_editor(
            si_df, num_rows="dynamic", use_container_width=True, key="e_si",
            hide_index=True,
            column_config={
                "subject":    st.column_config.TextColumn("Integrated Subject", width="medium"),
                "connection": st.column_config.TextColumn("Connection to Topic", width="large"),
                "daily_life": st.column_config.TextColumn("Daily Life Implementation", width="large"),
            },
        )

        st.markdown("**Character Building**")
        cb_df = pd.DataFrame([{"Dimensi": k, "Deskripsi": v} for k, v in data["character_building"].items()])
        st.data_editor(cb_df, use_container_width=True, key="e_cb", hide_index=True, disabled=["Dimensi"])

    with tab3:
        for i, m in enumerate(data["meetings"]):
            st.markdown(f"### Meeting {m['number']}: {m.get('topic', '')} (`{m['day_date']}`)")

            state_key = f"list_obj_{i}"
            if state_key not in st.session_state:
                initial_objs = list(m.get("objectives", []))
                while len(initial_objs) < 3:
                    initial_objs.append("")
                st.session_state[state_key] = initial_objs

            st.markdown("**Tujuan Pembelajaran:**")

            to_delete = None
            for j, obj in enumerate(st.session_state[state_key]):
                c1, c2 = st.columns([11, 1])
                new_obj = c1.text_area(
                    f"Tujuan M{m['number']}.{j+1}",
                    value=obj,
                    key=f"e_obj_{i}_{j}_{len(st.session_state[state_key])}",
                    label_visibility="collapsed",
                    height=68,
                )
                st.session_state[state_key][j] = new_obj

                if c2.button("🗑️", key=f"del_obj_{i}_{j}", help="Hapus tujuan ini"):
                    to_delete = j

            if to_delete is not None:
                st.session_state[state_key].pop(to_delete)
                st.rerun()

            if st.button("➕ Tambah Tujuan", key=f"add_obj_{i}"):
                st.session_state[state_key].append("")
                st.rerun()

            st.write("")

            stages_df = pd.DataFrame(m["stages"])
            st.data_editor(
                stages_df, use_container_width=True, hide_index=True,
                key=f"e_meet_{i}", disabled=["stage"],
                column_config={
                    "stage": st.column_config.TextColumn("Tahap", width="medium"),
                    "activity": st.column_config.TextColumn("Aktivitas", width="large"),
                    "values": st.column_config.TextColumn("Nilai", width="medium"),
                },
            )
            
            # Text area per meeting (Formative/Summative logic handled by AI prompt)
            st.text_area(
                f"Asesmen & Refleksi M{m['number']}", 
                value=m.get("assessment_reflection", ""), 
                key=f"e_ar_{i}",
                height=100
            )

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 Siapkan DOCX", type="primary", use_container_width=True):
            final = collect()
            st.session_state["docx_bytes"] = export_docx(final, info)
            st.success("File siap diunduh ⬇️")
        if "docx_bytes" in st.session_state:
            st.download_button(
                "⬇️ Download DOCX",
                data=st.session_state["docx_bytes"],
                file_name=f"Modul_{info['topic'][:20]}.docx",
                use_container_width=True,
            )
    with c2:
        if st.button("🧹 Reset Halaman", use_container_width=True):
            st.session_state["modul"] = None
            st.session_state.pop("docx_bytes", None)
            for k in list(st.session_state.keys()):
                if (k.startswith("list_obj_") or k.startswith("e_obj_")
                        or k.startswith("del_obj_") or k.startswith("add_obj_")
                        or k.startswith("e_ar_")):
                    del st.session_state[k]
            st.rerun()


# =========================================================
# FOOTER
# =========================================================
st.divider()
current_year = datetime.date.today().year
st.markdown(
    f"""
    <div style="
        text-align: center;
        padding: 18px 0 10px 0;
        margin-top: 20px;
        border-top: 1px solid rgba(128,128,128,0.2);
        color: #8a8a8a;
        font-size: 13px;
        line-height: 1.6;
    ">
        © {current_year} <strong> Frederick Sensei </strong> — All Rights Reserved.<br>
        <span style="font-size: 12px;">
            Modul Ajar Generator (No-API Mode · Cambridge English · CP dari CP_GRAPH)
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)