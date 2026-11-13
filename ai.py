"""Wrapper Ollama — AI Report Card Comments (Bloom + Predicate + No-pronoun aware)."""
import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# Konfigurasi
# =========================================================
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

client = OpenAI(api_key="ollama", base_url=f"{OLLAMA_HOST}/v1")


# =========================================================
# Utility
# =========================================================
def list_models():
    try:
        models = client.models.list()
        return sorted([m.id for m in models.data])
    except Exception:
        return []


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


def _word_count(text):
    return len((text or "").split())


# =========================================================
# Pronoun Guard — hindari he/she/his/her, pakai "the student"
# =========================================================
FORBIDDEN_PRONOUNS = [
    r"\bhe\b", r"\bshe\b", r"\bhe/she\b",
    r"\bhis\b", r"\bher\b", r"\bhis/her\b",
    r"\bhim\b", r"\bhimself\b", r"\bherself\b",
    r"\bthey\b", r"\bthem\b", r"\btheir\b",
]

_FORBIDDEN_RE = re.compile("|".join(FORBIDDEN_PRONOUNS), re.IGNORECASE)


def _contains_forbidden_pronoun(text):
    """True kalau ada pronoun terlarang di text."""
    return bool(_FORBIDDEN_RE.search(text or ""))


def _sanitize_pronouns(text, student_name=""):
    """
    Ganti pronoun terlarang dengan 'the student'.
    Dipakai sebagai fallback kalau AI tetap bandel.
    """
    if not text:
        return text

    # Possessive dulu (lebih spesifik)
    text = re.sub(r"\bhis/her\b", "the student's", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhis\b", "the student's", text, flags=re.IGNORECASE)
    text = re.sub(r"\bher\b", "the student's", text, flags=re.IGNORECASE)
    text = re.sub(r"\btheir\b", "the student's", text, flags=re.IGNORECASE)

    # Reflexive
    text = re.sub(r"\bhimself\b", "the student", text, flags=re.IGNORECASE)
    text = re.sub(r"\bherself\b", "the student", text, flags=re.IGNORECASE)

    # Subject / object
    text = re.sub(r"\bhe/she\b", "the student", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhe\b", "the student", text, flags=re.IGNORECASE)
    text = re.sub(r"\bshe\b", "the student", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhim\b", "the student", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthem\b", "the student", text, flags=re.IGNORECASE)

    # Rapikan dobel: "the student the student" → "the student"
    text = re.sub(
        r"\bthe student\s+the student\b",
        "the student",
        text,
        flags=re.IGNORECASE,
    )

    # Rapikan "the student's the student" → "the student's"
    text = re.sub(
        r"\bthe student's\s+the student\b",
        "the student's",
        text,
        flags=re.IGNORECASE,
    )

    # Kapitalisasi awal kalimat
    text = re.sub(
        r"(^|\.\s+|!\s+|\?\s+)the student",
        lambda m: m.group(1) + "The student",
        text,
    )

    return text


# =========================================================
# Bloom's Taxonomy Guide
# =========================================================
BLOOM_GUIDE = {
    "Mengingat":    "Remembering — recall of facts, terms, and basic concepts",
    "Memahami":     "Understanding — explaining ideas or concepts in own words",
    "Menerapkan":   "Applying — using knowledge in new situations or procedures",
    "Menganalisis": "Analyzing — drawing connections, comparing, breaking down ideas",
    "Mengevaluasi": "Evaluating — justifying a stand, critiquing, making judgements",
    "Mencipta":     "Creating — combining elements to produce something new",
}

DEFAULT_LEVEL = "Memahami"


# =========================================================
# Predicate Guide — variasi kata per predikat
# =========================================================
PREDICATE_GUIDE = {
    "A": {
        "label": "excellent",
        "synonyms": [
            "excellent", "outstanding", "advanced", "exceptional",
            "remarkable", "superior", "exemplary",
        ],
        "adverb": ["excellently", "outstandingly", "exceptionally", "remarkably"],
    },
    "B": {
        "label": "good enough",
        "synonyms": [
            "good", "good enough", "solid", "competent",
            "proficient", "satisfactory", "reliable",
        ],
        "adverb": ["well", "competently", "proficiently", "satisfactorily"],
    },
    "C": {
        "label": "developing",
        "synonyms": [
            "adequate", "moderate", "developing",
            "emerging", "basic", "reasonable",
        ],
        "adverb": ["fairly", "adequately", "moderately", "reasonably"],
    },
    "D": {
        "label": "needs support",
        "synonyms": [
            "needs support", "weak", "limited", "insufficient",
            "underdeveloped", "struggling", "inadequate",
        ],
        "adverb": ["limitedly", "insufficiently"],
    },
    "E": {
        "label": "Needs Intensive Support",
        "synonyms": [
            "Needs Intensive Support", "severely limited",
            "critically lacking", "well below expectations",
        ],
        "adverb": ["severely", "critically"],
    },
}


def _predicate_hint(pred):
    pred = (pred or "").upper()
    cfg = PREDICATE_GUIDE.get(pred)
    if not cfg:
        return f"{pred} — unspecified level"
    syns = ", ".join(cfg["synonyms"])
    advs = ", ".join(cfg["adverb"])
    return (
        f"{pred} = {cfg['label']}. "
        f"Choose ONE adjective from: {syns}. "
        f"Choose ONE adverb from: {advs}."
    )


# =========================================================
# Prompt Template
# =========================================================
PROMPT_TEMPLATE = """You are an experienced teacher writing report card comments in formal academic English.

TOPIC: {topic}
COGNITIVE LEVEL: {level} — {level_desc}

For the student below, generate TWO separate comments:
1. CONCEPT — knowledge and conceptual understanding
2. SKILL   — practical application and procedural ability

EACH comment MUST contain EXACTLY 3 sentences:
  S1 — state the student's current condition based on the predicate
  S2 — state the specific shortcoming or area needing improvement
  S3 — state a concrete, actionable way to improve

PREDICATE GUIDE (use the given synonyms — DO NOT always pick the first one):
  Concept Predicate : {concept_hint}
  Skill Predicate   : {skill_hint}

STUDENT:
  Name             : {name}
  Concept Predicate: {concept_pred}
  Skill Predicate  : {skill_pred}

PRONOUN RULES (STRICT — MUST FOLLOW):
- NEVER use "he", "she", "he/she", "his", "her", "his/her",
  "him", "himself", "herself", "they", "them", or "their".
- Refer to the student ONLY by the student's NAME or by "the student".
- In S1, use the student's name naturally.
- In S2 and S3, use "the student" or repeat the name.
- Example (correct):
  "Ahmad demonstrates strong understanding of algebra. The student
   occasionally overlooks the verification step. Practising systematic
   checking would help Ahmad reach mastery."
- Example (WRONG):
  "Ahmad demonstrates strong understanding. He overlooks steps. He should practise."

RULES:
- Maximum 50 words per comment.
- Grammar, articles, and punctuation must be correct English.
- The comment should match the {level} cognitive level
  (do NOT expect performance above or below this level).
- Pick ONE adjective and ONE adverb from the provided lists above.
- Do NOT add greetings, headings, or closing lines.
- Concept and Skill paragraphs must be worded differently.
- Concept and Skill should NOT use the same adjective as each other.

Respond ONLY with valid JSON:
{{"concept": "...", "skill": "..."}}
"""


def build_report_prompt(name, topic, concept_pred, skill_pred, level="Memahami"):
    level_desc = BLOOM_GUIDE.get(level, BLOOM_GUIDE[DEFAULT_LEVEL])
    return PROMPT_TEMPLATE.format(
        name=name,
        topic=topic,
        concept_pred=concept_pred,
        skill_pred=skill_pred,
        concept_hint=_predicate_hint(concept_pred),
        skill_hint=_predicate_hint(skill_pred),
        level=level,
        level_desc=level_desc,
    )


# =========================================================
# Generator
# =========================================================
def generate_report_comment(
    name, topic, concept_pred, skill_pred,
    model=None, level="Memahami",
):
    model = model or DEFAULT_MODEL
    prompt = build_report_prompt(name, topic, concept_pred, skill_pred, level)

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    try:
        resp = client.chat.completions.create(
            response_format={"type": "json_object"}, **kwargs
        )
    except Exception:
        resp = client.chat.completions.create(**kwargs)

    content = resp.choices[0].message.content or ""
    data = _parse_json(content)

    concept = (data.get("concept") or "").strip()
    skill = (data.get("skill") or "").strip()

    # Auto-fix kalau AI masih pakai pronoun terlarang
    concept = _sanitize_pronouns(concept, name)
    skill = _sanitize_pronouns(skill, name)

    return {"concept": concept, "skill": skill}


# =========================================================
# Test Koneksi
# =========================================================
def test_connection(model=None):
    model = model or DEFAULT_MODEL
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with one word: OK"}],
            max_tokens=5,
        )
        msg = (resp.choices[0].message.content or "").strip()
        return True, "OK: " + model + " -> " + msg[:40]
    except Exception as e:
        return False, "ERROR: " + str(e)