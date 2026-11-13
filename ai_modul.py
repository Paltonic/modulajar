"""ai_modul.py — Modul Ajar prompt builder + CP generator (No-API mode, English Cambridge).

Tidak ada panggilan API. Semua interaksi AI dilakukan manual via Claude.ai.
Website pemerintah (guru.kemendikdasmen.go.id) tidak dipakai lagi.
CP (Capaian Pembelajaran) ditulis dalam English Cambridge style.
"""
import json
import re


# =========================================================
# Local JSON parser
# =========================================================
def _parse_json(content):
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
        content = content.strip()
        if content.endswith("```"):
            content = content[:-3].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            return json.loads(content[start : end + 1])
        raise


# =========================================================
# KONSTANTA
# =========================================================
INQUIRY_STAGES = [
    "Tuning In", "Finding Out", "Sorting Out",
    "Going Further", "Making Conclusions", "Taking Actions",
]

NAKAMURA_PROFILE = [
    "Keimanan dan Ketakwaan terhadap Tuhan Yang Maha Esa",
    "Kewargaan", "Penalaran Kritis", "Kreativitas",
    "Kolaborasi", "Kemandirian", "Kesejahteraan", "Komunikasi",
]

BLOOM_LEVELS = [
    "Mengingat", "Memahami", "Menerapkan",
    "Menganalisis", "Mengevaluasi", "Mencipta",
]

NAKAMURA_LIST_STR = " | ".join(NAKAMURA_PROFILE)

KIRITSU_OPENING = (
    "1. Kiritsu (起立): Students stand up and greet the teacher in Japanese.\n"
    "2. Rei (礼): Students bow together.\n"
    "3. Chakuseki (着席): Students sit down, ready to learn."
)
KIRITSU_CLOSING = (
    "1. Kiritsu (起立): Students stand up.\n"
    "2. Rei (礼): Students bow and thank the teacher.\n"
    "3. Chakuseki (着席) or dismissal: Students sit down / leave politely."
)


# =========================================================
# STEP 0 — PROMPT CAPAIAN PEMBELAJARAN (CP) — English Cambridge
# =========================================================
CP_PROMPT_TEMPLATE = """You are a curriculum designer at Nakamura School using the Cambridge International Curriculum (Cambridge Lower Secondary / IGCSE standards), aligned with the Indonesian Kurikulum Merdeka framework.

Generate CAPAIAN PEMBELAJARAN (Learning Outcomes) for the following context.

=== CONTEXT ===
Subject         : {subject}
Class / Phase   : {class_level} / Fase {phase}
Duration        : {duration}
Term            : {term}

=== TOPICS (from meetings) ===
{meetings_str}

=== REFERENCE DOCUMENT ===
{reference_text}

=== TASKS ===
Generate MINIMUM 5 Learning Outcomes (CP) — recommended 5-8 items.

Each Learning Outcome MUST:
- Be written in FORMAL ACADEMIC ENGLISH (Cambridge style, NOT Bahasa Indonesia).
- Start with: "Students are able to ..." OR "Students can ..." OR "Students will be able to ...".
- Use ONE Cambridge-style action verb from Bloom's taxonomy, in ENGLISH:
  * Remembering: identify, recall, list, name, define
  * Understanding: explain, describe, summarise, classify, interpret
  * Applying: apply, demonstrate, use, implement, solve
  * Analyzing: analyse, compare, differentiate, examine, investigate
  * Evaluating: evaluate, justify, critique, assess, judge
  * Creating: design, create, construct, develop, produce
- Be specific to ONE or MORE of the topics listed above (NOT generic).
- Cover a balanced mix of: Knowledge (conceptual understanding), Skills (procedural / practical), and Application (real-world / Cambridge "learning objective" style).
- Be 1-2 sentences each. Distinct from one another (no repetition).
- NOT numbered (the app will number them automatically).
- Include a domain label prefix in square brackets at the START of each CP:
  [Knowledge]   — conceptual understanding
  [Skill]       — procedural / practical ability
  [Application] — real-world use / transfer

Cambridge learning objective style examples:
- "[Knowledge] Students are able to explain the fundamental concepts of artificial intelligence and its historical development."
- "[Skill] Students are able to apply a basic classification algorithm to a simple dataset and interpret the results."
- "[Application] Students are able to design a simple AI-assisted solution to a real-world problem and present it to peers."

=== OUTPUT (STRICT JSON, no markdown fences) ===
{{
  "capaian_pembelajaran": [
    "[Knowledge] Students are able to ...",
    "[Skill] Students are able to ...",
    "[Application] Students are able to ...",
    "[Knowledge] Students are able to ...",
    "[Skill] Students are able to ..."
  ]
}}

=== FINAL INSTRUCTION ===
Respond with the JSON object ONLY. No preamble, no explanation, no markdown fences.
"""


def build_cp_prompt(subject, class_level, phase, duration, term,
                    meetings, reference_text=""):
    """Bangun prompt CP (English Cambridge) dari topik-topik di meetings_list."""
    meetings_str = ""
    for m in meetings:
        meetings_str += (
            f"- Meeting {m['number']}: {m.get('topic', '(no topic)')} "
            f"(Level: {m.get('level', '-')})\n"
        )
    ref = reference_text[:4000] if reference_text else "(No document provided)"
    return CP_PROMPT_TEMPLATE.format(
        subject=subject, class_level=class_level, phase=phase,
        duration=duration, term=term,
        meetings_str=meetings_str, reference_text=ref,
    )


def _normalize_cp(data):
    """Ubah respon JSON Claude jadi list string CP. Robust ke berbagai format."""
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = (
            data.get("capaian_pembelajaran")
            or data.get("cp")
            or data.get("learning_outcomes")
            or data.get("items")
            or []
        )
        if isinstance(items, str):
            items = [items]
    elif isinstance(data, str):
        items = [data]
    else:
        items = []

    result = []
    for x in items:
        if isinstance(x, dict):
            x = x.get("teks") or x.get("text") or x.get("cp") or str(x)
        s = str(x).strip()
        # Hapus prefix nomor kalau ada (biar app yang nomori)
        s = re.sub(r"^\s*\d+[\.\)]\s*", "", s)
        if s:
            result.append(s)
    return result


# =========================================================
# PROMPT MODUL AJAR (Cambridge)
# =========================================================
PROMPT_TEMPLATE = """You are an experienced curriculum designer at Nakamura School.
Your pedagogical framework is the **Cambridge International Curriculum**
(Cambridge Lower Secondary / IGCSE standards). Use Cambridge terminology:
learning objectives, success criteria, active learning, differentiation,
formative assessment, and real-world application.

We need a complete lesson module (Modul Ajar) for MULTIPLE MEETINGS.

=== REFERENCE DOCUMENT (SYLLABUS/CURRICULUM) ===
{reference_text}

=== FIXED CONTEXT ===
Teacher           : {teacher}
Subject           : {subject}
Class / Phase     : {class_level} / Fase {phase}
Duration          : {duration}
Term / Semester   : {term}

=== MEETINGS & TOPICS ===
{meetings_input}

=== CAPAIAN PEMBELAJARAN (CP) — PROVIDED BY TEACHER ===
{cp_block}

Use the CP above as the PRIMARY reference:
- Every learning objective in each meeting MUST map to at least one CP.
- Activities should build toward achieving those CP.
- Do NOT invent new CP beyond this list.

=== YOUR TASKS ===
1. Align all activities with the Cambridge curriculum and the reference document (if provided).
2. INFER Prior Knowledge, Key Vocabulary, Guiding Questions, and Learning Objectives from the topics AND the CP above.
3. Design ACTIVE, student-centered, inquiry-based activities (no passive lecturing).
4. Include the **Kiritsu (起立) routine** as the opening of "Tuning In" and
   as the closing of the Assessment/Reflection section.

Produce output in STRICT JSON (no markdown fences).

=== SCHEMA ===
{{
  "learning_outcomes": "",
  "prior_knowledge":     ["Students already understand...", "Students are able to..."],
  "guiding_questions":   ["Essential question 1...", "Essential question 2..."],
  "enduring_understanding": "...",
  "key_vocabulary": [
     {{"jp": "kata jepang", "romaji": "romaji", "arti": "arti"}}
  ],
  "resources_materials": [
    "Textbook: Cambridge Global English Stage 7, pp. 45-50",
    "Journal: Journal of Japanese Language Education, Vol. 3 (2024)",
    "PPT: Nakamura School — Chapter 3 Slides"
  ],
  "subject_integration": {{
    "subjects": [
      {{
        "subject": "Science",
        "connection": "Students apply measurement and data-handling skills...",
        "daily_life": "Measuring ingredients in cooking, reading temperature..."
      }}
    ]
  }},
  "character_building": {{
     "Keimanan dan Ketakwaan terhadap Tuhan Yang Maha Esa": "...",
     "Kewargaan": "...", "Penalaran Kritis": "...", "Kreativitas": "...",
     "Kolaborasi": "...", "Kemandirian": "...", "Kesejahteraan": "...", "Komunikasi": "..."
  }},
  "meetings": [
     {{
       "number": 1,
       "topic": "Topic of meeting 1",
       "level": "Cognitive level of meeting 1",
       "day_date": "<exact copy of the Date given for this meeting>",
       "objectives": [
         "By the end of the lesson, students will be able to ... (LO 1)",
         "By the end of the lesson, students will be able to ... (LO 2)",
         "By the end of the lesson, students will be able to ... (LO 3)"
       ],
       "stages": [
         {{"stage": "Tuning In",         "activity": "{kiritsu_opening}\\n4. Teacher shows a short video...\\n5. Students ask critical questions...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Finding Out",        "activity": "1. Students read ...\\n2. Students collect data ...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Sorting Out",        "activity": "1. Students classify ...\\n2. Students discuss ...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Going Further",      "activity": "1. Students investigate ...\\n2. Students solve ...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Making Conclusions", "activity": "1. Students present ...\\n2. Students reflect ...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Taking Actions",     "activity": "1. Students apply ...\\n2. Students share ...", "values": "<ONE dimension OR hyphen>"}}
       ]
     }}
  ],
  "assessment_reflection": "Formative: ...\\nSummative: ...\\nReflection: ...\\n\\nClosing routine:\\n{kiritsu_closing}"
}}

=== RULES ===
- Output valid JSON only, NO ```json fences, NO preamble, NO explanation.
- ALL narrative fields MUST be in ENGLISH (except key_vocabulary jp/romaji/arti).
- Cambridge International Curriculum terminology must be used.
- "learning_outcomes" MUST be an EMPTY STRING "" — the app fills it from the CP list above.
- "resources_materials" MUST cite specific examples.
- "subject_integration" MUST be an OBJECT with key "subjects". Provide 2-3 subjects.
- Each meeting MUST have EXACTLY 3 learning objectives.
- Each objective MUST map to at least one CP listed above.
- "activity" fields MUST contain MULTIPLE numbered points (3-5), separated by "\\n".
- The FIRST activity of "Tuning In" MUST be the Kiritsu opening routine.
- The LAST part of "assessment_reflection" MUST include the Kiritsu closing routine.
- "values" for each stage = EXACTLY ONE dimension from: {nakamura_list}, OR "-".
- "day_date" MUST be an EXACT copy of the Date given.
- The "meetings" array MUST contain EXACTLY {n_meetings} objects.

=== KIRITSU OPENING ===
{kiritsu_opening}

=== KIRITSU CLOSING ===
{kiritsu_closing}

=== FINAL INSTRUCTION ===
Respond with the JSON object ONLY. Do not add any text before or after the JSON.
"""


def build_modul_prompt(teacher, subject, class_level, phase, duration, term,
                       meetings, reference_text="", cp_list=None):
    meetings_str = ""
    for m in meetings:
        date_str = m.get("date") or "TBD"
        meetings_str += (
            f"- Meeting {m['number']}: Date = {date_str} | "
            f"Topic = {m['topic']} | Level = {m['level']}\n"
        )

    cp_list = cp_list or []
    if cp_list:
        cp_block = "\n".join(f"{i+1}. {cp}" for i, cp in enumerate(cp_list))
    else:
        cp_block = "(No CP provided — infer from topics)"

    ref = reference_text[:6000] if reference_text else "(No document provided)"
    return PROMPT_TEMPLATE.format(
        teacher=teacher, subject=subject, class_level=class_level,
        phase=phase, duration=duration, term=term,
        meetings_input=meetings_str, reference_text=ref,
        cp_block=cp_block,
        n_meetings=len(meetings), nakamura_list=NAKAMURA_LIST_STR,
        kiritsu_opening=KIRITSU_OPENING, kiritsu_closing=KIRITSU_CLOSING,
    )


# =========================================================
# NORMALIZER — dipakai app.py untuk parse JSON modul
# =========================================================
def _as_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip()
    return [s] if s else []


def _as_text(v, default="-"):
    if v is None:
        return default
    if isinstance(v, str):
        s = v.strip()
        return s if s else default
    if isinstance(v, (list, tuple)):
        lines = []
        for item in v:
            if isinstance(item, (dict, list, tuple)):
                sub = _as_text(item, default="")
                if sub:
                    lines.append(f"- {sub}")
            else:
                s = str(item).strip()
                if s:
                    lines.append(f"- {s}")
        return "\n".join(lines) if lines else default
    if isinstance(v, dict):
        lines = [f"- {k}: {_as_text(val)}" for k, val in v.items()]
        return "\n".join(lines) if lines else default
    s = str(v).strip()
    return s if s else default


def _coerce_value(v):
    if v is None:
        return "-"
    if isinstance(v, (list, tuple)):
        v = " ".join(str(x) for x in v)
    elif isinstance(v, dict):
        v = " ".join(str(x) for x in v.values())
    v = str(v).strip()
    if not v:
        return "-"
    if v in NAKAMURA_PROFILE:
        return v
    low = v.lower()
    for dim in NAKAMURA_PROFILE:
        if dim.lower() in low or low in dim.lower():
            return dim
    keywords = {
        "kolaborasi": "Kolaborasi", "kelompok": "Kolaborasi", "diskusi": "Kolaborasi",
        "kritis": "Penalaran Kritis", "analis": "Penalaran Kritis",
        "kreatif": "Kreativitas", "karya": "Kreativitas",
        "mandiri": "Kemandirian", "sendiri": "Kemandirian",
        "komunikasi": "Komunikasi", "presentasi": "Komunikasi",
        "kewargaan": "Kewargaan", "sopan": "Kewargaan",
        "sejahtera": "Kesejahteraan", "refleksi": "Kesejahteraan",
        "tuhan": "Keimanan dan Ketakwaan terhadap Tuhan Yang Maha Esa",
        "iman": "Keimanan dan Ketakwaan terhadap Tuhan Yang Maha Esa",
    }
    for kw, dim in keywords.items():
        if kw in low:
            return dim
    return "-"


def _normalize_subject_integration(si):
    if isinstance(si, dict):
        subjects_raw = si.get("subjects") or []
    elif isinstance(si, str) and si.strip():
        subjects_raw = [{"subject": "General", "connection": si.strip(), "daily_life": "-"}]
    else:
        subjects_raw = []
    subjects = []
    for s in subjects_raw:
        if isinstance(s, dict):
            subjects.append({
                "subject": _as_text(s.get("subject"), "-"),
                "connection": _as_text(s.get("connection"), "-"),
                "daily_life": _as_text(s.get("daily_life"), "-"),
            })
        elif isinstance(s, str) and s.strip():
            subjects.append({"subject": s.strip(), "connection": "-", "daily_life": "-"})
    return {"subjects": subjects}


def _normalize(data, meetings_input):
    d = data if isinstance(data, dict) else {}

    cb = d.get("character_building") or {}
    if not isinstance(cb, dict):
        cb = {}
    cb = {dim: _as_text(cb.get(dim), "-") for dim in NAKAMURA_PROFILE}

    meetings_raw = d.get("meetings") or []
    if not isinstance(meetings_raw, list):
        meetings_raw = []

    normalized_meetings = []
    for i, m_in in enumerate(meetings_input):
        src = meetings_raw[i] if i < len(meetings_raw) and isinstance(meetings_raw[i], dict) else {}
        stages_raw = src.get("stages") or []
        if not isinstance(stages_raw, list):
            stages_raw = []
        by_name = {s.get("stage"): s for s in stages_raw
                   if isinstance(s, dict) and s.get("stage")}

        stages = []
        for sname in INQUIRY_STAGES:
            s = by_name.get(sname, {})
            act_text = _as_text(s.get("activity"), "-")
            act_text = re.sub(r'(?<!\n)\s*(\d+)[\.\)]\s+', r'\n\1. ', act_text).strip()
            stages.append({
                "stage": sname,
                "activity": act_text,
                "values": _coerce_value(s.get("values")),
            })

        objs = _as_list(src.get("objectives"))
        while len(objs) < 3:
            objs.append("-")

        normalized_meetings.append({
            "number": int(src.get("number") or (i + 1)),
            "topic": _as_text(src.get("topic"), m_in["topic"]),
            "level": _as_text(src.get("level"), m_in["level"]),
            "day_date": _as_text(src.get("day_date"), m_in.get("date") or "TBD"),
            "objectives": objs,
            "stages": stages,
        })

    kv_raw = d.get("key_vocabulary") or []
    if isinstance(kv_raw, str):
        kv_raw = [kv_raw]
    if not isinstance(kv_raw, list):
        kv_raw = []
    kv = []
    for item in kv_raw:
        if isinstance(item, dict):
            kv.append({
                "jp": _as_text(item.get("jp"), ""),
                "romaji": _as_text(item.get("romaji"), ""),
                "arti": _as_text(item.get("arti"), ""),
            })
        else:
            kv.append({"jp": _as_text(item, ""), "romaji": "", "arti": ""})

    ar_text = _as_text(d.get("assessment_reflection"), "-")
    ar_text = re.sub(r'(?<!\n)\s*(\d+)[\.\)]\s+', r'\n\1. ', ar_text).strip()

    return {
        "learning_outcomes": "",
        "prior_knowledge": _as_list(d.get("prior_knowledge")) or ["-"],
        "guiding_questions": _as_list(d.get("guiding_questions")) or ["-"],
        "enduring_understanding": _as_text(d.get("enduring_understanding"), "-"),
        "key_vocabulary": kv,
        "resources_materials": _as_list(d.get("resources_materials")) or ["-"],
        "subject_integration": _normalize_subject_integration(d.get("subject_integration")),
        "character_building": cb,
        "meetings": normalized_meetings,
        "assessment_reflection": ar_text,
    }