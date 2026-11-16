"""ai_modul.py — Merged core for Modul Ajar (Claude prompt builder + CP + normaliser).

- No API calls: all AI interaction happens manually on Claude.ai
- CP prompt builder (English / Cambridge style)
- Modul Ajar prompt builder (British English + Nakamura 8-dimensions + Kiritsu)
- Robust JSON parser & normaliser ready to feed app.py
"""
import json
import re

# =========================================================
# CONSTANTS
# =========================================================
INQUIRY_STAGES = [
    "Tuning In", "Finding Out", "Sorting Out",
    "Going Further", "Making Conclusions", "Taking Actions",
]

# Alias map to repair minor typos from Claude
STAGE_ALIASES = {
    "tuning in": "Tuning In",
    "finding out": "Finding Out",
    "sorting out": "Sorting Out",
    "going further": "Going Further",
    "making conclusions": "Making Conclusions",
    "making conclusion": "Making Conclusions",
    "making-conclusion": "Making Conclusions",
    "taking actions": "Taking Actions",
    "taking action": "Taking Actions",
}

BLOOM_LEVELS = [
    "Mengingat", "Memahami", "Menerapkan",
    "Menganalisis", "Mengevaluasi", "Mencipta",
]

SUBJECTS = ["Health and Physical Education", "Computer Science"]

# Nakamura School — 8 dimensions (Profil Pelajar Pancasila adapted)
NAKAMURA_PROFILE = [
    "Keimanan dan Ketakwaan terhadap Tuhan Yang Maha Esa",
    "Kewargaan", "Penalaran Kritis", "Kreativitas",
    "Kolaborasi", "Kemandirian", "Kesejahteraan", "Komunikasi",
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
# CP_GRAPH — populate with school data
# key: (fase, kelas, subject) → list of CP strings
# =========================================================
CP_GRAPH = {
    ("D", "J2", "Computer Science"): [
        "Students will be able to design, develop, test, deploy and evaluate modern, responsive and accessible websites by using semantic HTML to create well-structured, meaningful and search-engine-friendly documents, and CSS to implement maintainable layouts and visual systems through mobile-first responsive design, Flexbox, CSS Grid, custom properties, media queries and component-based styling conventions, while applying accessibility best practices such as appropriate landmark elements, ARIA roles and attributes where necessary, keyboard navigation, focus management, colour-contrast compliance and screen-reader-friendly content. They will use JavaScript ES6+ to add interactivity and handle asynchronous data, demonstrating competence in variables, functions, modules, array and object manipulation, DOM selection and manipulation, event handling and delegation, form validation and user feedback, error handling with try/catch, promises and async/await, fetching and processing data from external APIs, managing loading and error states, and using browser storage such as localStorage where appropriate. Learners will apply Bootstrap to accelerate the creation of consistent and responsive user interfaces by customising its grid system, spacing utilities, typography and components, overriding default variables and styles to maintain a coherent visual identity, and ensuring that Bootstrap-based interfaces remain accessible and responsive across devices. They will use React to build reusable component-based interfaces with state management through hooks such as useState, useEffect, useContext and useReducer, managing component lifecycle and side effects, lifting state where necessary, passing data through props, handling events and forms in a controlled manner, conditionally rendering UI, composing components into modular and maintainable file structures, and applying basic testing and debugging practices. Learners will employ Next.js to implement routing and appropriate rendering strategies, including Static Site Generation (SSG), Server-Side Rendering (SSR), Incremental Static Regeneration (ISR) and Client-Side Rendering (CSR), selecting strategies according to content dynamism and performance requirements, while applying basic SEO optimisation through metadata management, semantic markup, sitemap and robots considerations, image optimisation using the Next.js Image component, font optimisation, code splitting and performance best practices. Finally, they will use Netlify to build and deploy applications automatically to a public domain through Git repository integration, configuring build commands and publish directories, managing environment variables, redirects and rewrites, integrating basic serverless functions where required, using deploy previews and rollbacks, and applying version control with Git and collaborative workflows such as branching, pull requests and code review. Throughout the process, learners will demonstrate systematic problem-solving, document their design and development decisions, evaluate the usability, accessibility, performance and security of their deployed applications, and consider ethical, social and professional responsibilities in the creation and publication of web-based solutions.",
    ],
    ("D", "J3", "Computer Science"): [
        "Students will be able to apply Design Thinking as a structured, human-centred approach to problem-solving by empathising with users through interviews and observations, defining problems clearly using tools such as personas and journey maps, generating and evaluating ideas through divergent and convergent thinking, and building low-fidelity and high-fidelity prototypes that are tested and iterated based on user feedback. They will explain and perform operations on binary number systems, including conversion between binary, decimal, octal and hexadecimal, binary arithmetic (addition, subtraction and multiplication), representation of signed and unsigned integers, and the basic principles of floating-point representation. Learners will describe the fundamentals of computer networks, including network topologies (bus, star, ring, mesh), transmission media, common network devices, the OSI and TCP/IP reference models, IP addressing and subnetting, and core protocols such as HTTP, DNS, DHCP and TCP/UDP, as well as apply basic troubleshooting techniques. They will explain the organisation and architecture of computer systems, including the von Neumann architecture, CPU components (ALU, control unit, registers), the instruction cycle, pipelining, memory hierarchy (registers, cache, RAM, secondary storage), input/output mechanisms, and the distinction between RISC and CISC architectures. Learners will write basic C++ programs using variables, data types, operators, control structures (sequence, selection and iteration), functions, arrays, basic pointers, file input/output and modular programming practices, while applying debugging techniques and adhering to good coding conventions. They will design database entity-relationship diagrams (ERDs) by identifying entities, attributes and relationships, specifying cardinality and participation constraints, recognising weak entities and associative entities, applying normalisation principles up to the third normal form (3NF), and mapping ERDs to relational schemas. Throughout, learners will demonstrate logical reasoning, systematic problem-solving, collaboration and effective communication of technical solutions, and will consider ethical, social and professional responsibilities in the design and use of computing systems.",
    ],
    ("D", "J1", "Health and Physical Education"): [
        "At the end of Phase D, students are projected to be able to practise the analysis of specific movement skills, carry out fitness training in accordance with established principles, and prioritise personal and social responsibility, and broadly, the Physical Education, Sport, and Health (PJOK) learning outcomes for junior high school are divided into four main elements, namely movement skills, which involve practising the results of specific movement analysis covering games and sports such as invasion, net, and field games, gymnastics, rhythmic movement, and water sports, movement knowledge, which involves understanding, analysing, and evaluating the concepts and strategies of various physical activities, movement utilisation, which involves improving physical fitness related to both health and skills and understanding the prevention of non-communicable diseases, and character development, which involves demonstrating cooperation, fair play values, and independence in monitoring personal fitness.",
    ],
    ("D", "J2", "Health and Physical Education"): [
        "At the end of Phase D, students are projected to be able to practise the analysis of specific movement skills, carry out fitness training in accordance with established principles, and prioritise personal and social responsibility, and broadly, the Physical Education, Sport, and Health (PJOK) learning outcomes for junior high school are divided into four main elements, namely movement skills, which involve practising the results of specific movement analysis covering games and sports such as invasion, net, and field games, gymnastics, rhythmic movement, and water sports, movement knowledge, which involves understanding, analysing, and evaluating the concepts and strategies of various physical activities, movement utilisation, which involves improving physical fitness related to both health and skills and understanding the prevention of non-communicable diseases, and character development, which involves demonstrating cooperation, fair play values, and independence in monitoring personal fitness.",
    ],
    ("E", "S1", "Health and Physical Education"): [
        "At the end of phase E, students focus on evaluating, applying and refining movement skills and healthy lifestyle behaviours, and broadly, the Phase E learning outcomes are divided into four main elements, namely movement skills, in which students are able to design, apply, refine and develop movement strategies in various challenging situations through varied activities such as games, athletics, gymnastics, rhythmic movement and water sports, movement knowledge, in which students analyse the impact of applying movement concepts on skills and understand scientific facts, mechanical principles and tactical strategies in sport, movement utilisation, in which students evaluate the impact of physical activity on fitness and health and apply biomotor training and healthy lifestyle practices, and character and movement values development, in which students demonstrate fair play, ethical behaviour, leadership, collaboration and resilience in facing training and competition pressure.",
    ],
    ("E", "S1", "Computer Science"): [
        "Students will be able to use Google Colab as a cloud-based computational environment to write, execute, debug and document Python code for end-to-end data science workflows, including organising notebooks with Markdown documentation, installing and managing third-party libraries, mounting Google Drive for persistent storage, importing and exporting data from local and cloud sources, using GPU and TPU runtimes where appropriate, and collaborating in real time through shared notebooks, comments and version history; collect data systematically from multiple sources by performing web scraping using libraries such as Requests, BeautifulSoup, Scrapy and Selenium to extract data from static and dynamically rendered web pages while handling pagination, rate limiting and session management, and by collecting data through public APIs with authentication, JSON and XML response handling and rate-limit management, as well as through file-based sources such as CSV, Excel, JSON and SQL databases and open data portals, while respecting legal and ethical considerations including robots.txt protocols, terms of service, copyright, data privacy regulations such as GDPR principles, consent and anonymisation of personal data; clean and prepare raw data for analysis by identifying and handling missing values through deletion, imputation or interpolation, removing duplicate records, detecting and treating outliers using statistical and visual methods, standardising inconsistent formats such as dates, currencies and text encodings, converting data types appropriately, normalising and scaling numerical features, encoding categorical variables, and correcting structural errors such as misaligned columns and inconsistent naming conventions; modify and transform data using pandas and NumPy through filtering, sorting, merging, joining, concatenating and reshaping datasets, grouping and aggregating data with pivot tables and groupby operations, creating derived features and calculated columns, applying window functions and time-series transformations, and restructuring data between wide and long formats to suit analytical needs; perform exploratory data analysis by computing descriptive statistics, examining distributions, identifying correlations and patterns and formulating initial hypotheses, and create meaningful and accurate data visualisations using Matplotlib, Seaborn and Plotly by selecting appropriate chart types for different data and analytical purposes, applying principles of clarity, accuracy, labelling and accessibility, customising visual elements such as colours, scales and annotations, and constructing multi-panel and interactive visualisations to communicate insights effectively; and apply foundational data science concepts and methods—including descriptive and inferential statistics, correlation and regression analysis, basic hypothesis testing and introductory predictive modelling using libraries such as scikit-learn—to derive evidence-based insights and support decision-making, communicate findings through well-documented notebooks, structured reports and visual narratives, evaluate the quality, limitations, biases and ethical implications of their data and results, ensure reproducibility through clear documentation of code, data sources and analytical decisions, and demonstrate systematic problem-solving, critical thinking and effective communication of data-driven conclusions in individual and collaborative settings. They will design, implement and evaluate AI agents to automate and augment data science workflows—including agent-based data collection, cleaning, analysis and visualisation—using appropriate frameworks and tools while assessing their reliability, limitations and ethical implications.",
    ],
    ("F", "S2", "Health and Physical Education"): [
        "At the end of this phase F, students focus on three main elements of skill and character development, namely moving skilfully, in which they evaluate specific movement skills and strategies to improve performance in various challenging situations, learning through movement, in which they apply and evaluate movement strategies in new situations, uphold fair play, and reflect on the influence of ethical behaviour on physical activity, and evaluate decision-making strategies in teamwork involving leadership and collaboration, and living an active lifestyle, in which they actively participate in fitness activities and evaluate the impact and effectiveness of their strategies on long-term health.",
    ],
    ("F", "S2", "Computer Science"): [
        "Students will be able to explain the foundational concepts, scope and societal implications of artificial intelligence and apply machine learning workflows—including problem framing, data preparation, feature engineering, model selection, training, evaluation and interpretation—by distinguishing and implementing supervised learning models for classification and regression tasks using appropriate algorithms such as logistic regression, decision trees, random forests, support vector machines, k-nearest neighbours and linear regression, and unsupervised learning models such as clustering and dimensionality reduction using k-means, hierarchical clustering and principal component analysis; they will build, train and evaluate deep learning models using neural networks, including feedforward networks, convolutional neural networks and recurrent networks where appropriate, applying techniques such as activation functions, loss functions, optimisers, regularisation, dropout and hyperparameter tuning, and will evaluate model performance using suitable metrics including accuracy, precision, recall, F1-score, confusion matrices, mean absolute error, mean squared error, R-squared and cross-validation; they will apply natural language processing models and techniques—including text preprocessing, tokenisation, stemming and lemmatisation, stop-word removal, bag-of-words and TF-IDF representations, word embeddings, sentiment analysis and basic sequence modelling—to process and analyse textual data; and they will interpret results, assess model limitations such as overfitting, bias and data leakage, consider ethical, legal and social implications including privacy, fairness and transparency, communicate findings through structured documentation and visualisations, and demonstrate systematic problem-solving, critical thinking and responsible practice in individual and collaborative projects.",
    ],
    # add further entries as needed
}


def get_cp(phase, class_level, subject):
    key = (
        str(phase).strip().upper(),
        str(class_level).strip().upper(),
        str(subject).strip(),
    )
    return list(CP_GRAPH.get(key, []))


# =========================================================
# JSON parser
# =========================================================
def _parse_json(text: str):
    """Extract & parse JSON from Claude response (tolerates ```json fences)."""
    s = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
    if m:
        s = m.group(1).strip()
    else:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start:end + 1]
    return json.loads(s)


# =========================================================
# CP PROMPT (English / Cambridge) — generate learning outcomes
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
- Start with: "Students are able to ..." OR "Students will be able to ...".
- Use ONE Cambridge-style action verb from Bloom's taxonomy, in ENGLISH:
  * Remembering: identify, recall, list, name, define
  * Understanding: explain, describe, summarise, classify, interpret
  * Applying: apply, demonstrate, use, implement, solve
  * Analyzing: analyse, compare, differentiate, examine, investigate
  * Evaluating: evaluate, justify, critique, assess, judge
  * Creating: design, create, construct, develop, produce
- Be specific to ONE or MORE of the topics listed above (NOT generic).
- Cover a balanced mix of Knowledge (conceptual), Skill (procedural), and Application (real-world).
- Be 1-2 sentences each. Distinct from one another.
- NOT numbered (the app numbers them automatically).
- Include a domain label prefix at the START of each CP:
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
    """Build the CP-generation prompt (English / Cambridge style)."""
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
    """Convert a Claude JSON response into a clean list of CP strings."""
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
        s = re.sub(r"^\s*\d+[\.\)]\s*", "", s)  # strip manual numbering
        if s:
            result.append(s)
    return result


# =========================================================
# MODUL AJAR PROMPT — Claude, Cambridge English + Nakamura + Kiritsu
# =========================================================
PROMPT_TEMPLATE = """You are an experienced curriculum designer at Nakamura School.
Your pedagogical framework is the **Cambridge International Curriculum**
(Cambridge Lower Secondary / IGCSE standards), aligned with the Indonesian
Kurikulum Merdeka framework. Use Cambridge terminology: learning objectives,
success criteria, active learning, differentiation, formative assessment
and real-world application.

⚠️ CRITICAL LANGUAGE REQUIREMENT ⚠️
ALL narrative values in the output JSON MUST be written in **Cambridge English
(British English)**, formal academic register, as used in Cambridge International
Schools. Do NOT use Bahasa Indonesia for any narrative field.
**EXCEPTION:** the "jp" field in key_vocabulary MUST be Japanese (Kanji / Kana)
and "romaji" MUST be Romaji. Field names in the schema remain EXACTLY as shown.

British English spelling rules (MANDATORY):
- -ise endings: organise, analyse, recognise, summarise, characterise, emphasise, memorise, realise, prioritise, standardise.
- -our endings: behaviour, colour, favour, labour, neighbour, honour.
- -re endings: centre, metre, theatre, litre, fibre.
- -ce (noun) / -se (verb): practice (noun) vs practise (verb).
- -ogue: catalogue, dialogue, analogue.
- Double L: travelling, cancelled, modelling, labelling, fulfilment.
- AVOID American spellings: no "organize", "analyze", "color", "behavior", "center", "recognize", "summarize", "program" (use "programme").
- No contractions ("do not", not "don't").

=== REFERENCE DOCUMENT (SYLLABUS / CURRICULUM) ===
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
- Activities must build toward achieving those CP.
- Do NOT invent new CP beyond this list.

=== YOUR TASKS ===
1. Align all activities with the Cambridge curriculum and the reference document (if provided).
2. INFER Prior Knowledge, Key Vocabulary, Guiding Questions and Learning Objectives from the topics AND the CP above.
3. Design ACTIVE, student-centred, inquiry-based activities (no passive lecturing).
4. The "Tuning In" stage of EVERY meeting MUST begin with the Kiritsu Rei routine.
5. The "assessment_reflection" field MUST end with the Kiritsu closing routine.

=== SCHEMA (STRICT — follow exactly) ===
{{
  "learning_outcomes": "",
  "prior_knowledge":     ["Students already understand...", "Students are able to..."],
  "guiding_questions":   ["Essential question 1...", "Essential question 2..."],
  "enduring_understanding": "...",
  "key_vocabulary": [
     {{"jp": "Japanese term (Kanji / Kana)", "romaji": "romanisation", "arti": "meaning in Cambridge English"}}
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
         {{"stage": "Tuning In",         "activity": "{kiritsu_opening}\\n4. Teacher shows a short video...\\n5. Students ask critical questions...", "values": "<ONE Nakamura dimension OR hyphen>"}},
         {{"stage": "Finding Out",        "activity": "1. Students read ...\\n2. Students collect data ...\\n3. Students record observations ...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Sorting Out",        "activity": "1. Students classify ...\\n2. Students discuss ...\\n3. Students draft ...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Going Further",      "activity": "1. Students investigate ...\\n2. Students solve ...\\n3. Students extend ...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Making Conclusions", "activity": "1. Students present ...\\n2. Students reflect ...\\n3. Students summarise ...", "values": "<ONE dimension OR hyphen>"}},
         {{"stage": "Taking Actions",     "activity": "1. Students apply ...\\n2. Students share ...\\n3. Students commit ...", "values": "<ONE dimension OR hyphen>"}}
       ]
     }}
  ],
  "assessment_reflection": "Formative: ...\\nSummative: ...\\nReflection: ...\\n\\nClosing routine:\\n{kiritsu_closing}"
}}

=== RULES ===
- Output valid JSON only, NO ```json fences, NO preamble, NO explanation.
- ALL narrative fields MUST be in British English (except key_vocabulary jp/romaji/arti).
- "learning_outcomes" MUST be an EMPTY STRING "" — the app fills it from the CP list above.
- Each meeting MUST have EXACTLY 3 learning objectives.
- Each objective MUST map to at least one CP listed above.
- "activity" fields MUST contain MULTIPLE numbered points (3-5), separated by "\\n".
- The FIRST activity of "Tuning In" MUST be the Kiritsu opening routine.
- The LAST part of "assessment_reflection" MUST include the Kiritsu closing routine.
- "values" for each stage MUST be EXACTLY ONE dimension from:
  {nakamura_list}
  ... OR the string "-" if no dimension applies.
- "day_date" MUST be an EXACT copy of the Date given for that meeting.
- The "meetings" array MUST contain EXACTLY {n_meetings} object(s).
- "subject_integration" MUST be an OBJECT with key "subjects" (2-3 subjects).
- "resources_materials" MUST cite specific, credible examples.

=== KIRITSU OPENING ===
{kiritsu_opening}

=== KIRITSU CLOSING ===
{kiritsu_closing}

=== FINAL INSTRUCTION ===
Respond with the JSON object ONLY. Do not add any text before or after the JSON.
"""


def build_modul_prompt(teacher, subject, class_level, phase, duration, term,
                       meetings, reference_text="", cp_list=None):
    """Build the Modul Ajar prompt for Claude (British English + Nakamura + Kiritsu)."""
    meetings_str = ""
    for m in meetings:
        date_str = m.get("date") or "TBD"
        meetings_str += (
            f"- Meeting {m['number']}: Date = {date_str} | "
            f"Topic = {m['topic']} | Level = {m['level']}\n"
        )

    cp_list = cp_list or []
    cp_block = (
        "\n".join(f"{i+1}. {cp}" for i, cp in enumerate(cp_list))
        if cp_list else "(No CP provided — infer from topics)"
    )

    ref = reference_text[:6000] if reference_text else "(No document provided)"
    return PROMPT_TEMPLATE.format(
        teacher=teacher, subject=subject, class_level=class_level,
        phase=phase, duration=duration, term=term,
        meetings_input=meetings_str, reference_text=ref,
        cp_block=cp_block,
        n_meetings=len(meetings),
        nakamura_list=NAKAMURA_LIST_STR,
        kiritsu_opening=KIRITSU_OPENING,
        kiritsu_closing=KIRITSU_CLOSING,
    )


# =========================================================
# NORMALISER (robust — matches app.py schema)
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
    """Force `values` to one of the 8 Nakamura dimensions, or '-'."""
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


def _fix_numbering(text: str) -> str:
    """Ensure numbered lists (1. 2. 3.) start on their own line."""
    return re.sub(r'(?<!\n)\s*(\d+)[\.\)]\s+', r'\n\1. ', text).strip()


def _normalize(data, meetings_input):
    """Coerce Claude JSON into the schema app.py expects."""
    d = data if isinstance(data, dict) else {}

    # --- character_building: always 8 Nakamura dimensions
    cb_raw = d.get("character_building") or {}
    if not isinstance(cb_raw, dict):
        cb_raw = {}
    cb = {dim: _as_text(cb_raw.get(dim), "-") for dim in NAKAMURA_PROFILE}

    # --- meetings: exactly one entry per meeting_input, 6 ordered stages each
    meetings_raw = d.get("meetings") or []
    if not isinstance(meetings_raw, list):
        meetings_raw = []

    normalized_meetings = []
    for i, m_in in enumerate(meetings_input):
        src = meetings_raw[i] if i < len(meetings_raw) and isinstance(meetings_raw[i], dict) else {}
        stages_raw = src.get("stages") or []
        if not isinstance(stages_raw, list):
            stages_raw = []

        # Normalise stage names via alias map
        by_name = {}
        for s in stages_raw:
            if not isinstance(s, dict):
                continue
            raw_name = str(s.get("stage", "")).strip()
            canon = STAGE_ALIASES.get(raw_name.lower(), raw_name)
            if canon in INQUIRY_STAGES:
                by_name[canon] = s

        stages = []
        for sname in INQUIRY_STAGES:
            s = by_name.get(sname, {})
            act_text = _fix_numbering(_as_text(s.get("activity"), "-"))
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
            "topic": _as_text(src.get("topic"), m_in.get("topic", "-")),
            "level": _as_text(src.get("level"), m_in.get("level", "-")),
            "day_date": _as_text(
                src.get("day_date") or src.get("date"),
                m_in.get("date") or "TBD",
            ),
            "objectives": objs,
            "stages": stages,
        })

    # --- key_vocabulary (jp / romaji / arti)
    kv_raw = d.get("key_vocabulary") or []
    if isinstance(kv_raw, str):
        kv_raw = [kv_raw]
    if not isinstance(kv_raw, list):
        kv_raw = []
    kv = []
    for item in kv_raw:
        if isinstance(item, dict):
            kv.append({
                "jp": _as_text(item.get("jp") or item.get("word") or item.get("term"), ""),
                "romaji": _as_text(item.get("romaji") or item.get("pronunciation"), ""),
                "arti": _as_text(item.get("arti") or item.get("meaning"), ""),
            })
        else:
            kv.append({"jp": _as_text(item, ""), "romaji": "", "arti": ""})

    ar_text = _fix_numbering(_as_text(d.get("assessment_reflection"), "-"))

    return {
        "learning_outcomes": "",  # app fills from CP list
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