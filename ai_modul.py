"""ai_modul.py — Core: prompt builder, JSON parser, CP lookup."""
import json
import re

# ---------------------------------------------------------
# Konstanta
# ---------------------------------------------------------
BLOOM_LEVELS = [
    "Mengingat", "Memahami", "Menerapkan",
    "Menganalisis", "Mengevaluasi", "Mencipta",
]

SUBJECTS = [
    "Language and Literature",
    "Language Acquisition",
    "Health and Physical Education",
    "Sciences",
    "Mathematics",
    "Arts",
    "Design",
    "Individuals and Societies",
]

# ---------------------------------------------------------
# CP_GRAPH — ISI SENDIRI sesuai data sekolah Anda
# Format key: (fase, kelas, subject)  →  value: list CP
# Contoh di bawah, silakan tambah/hapus.
# ---------------------------------------------------------
CP_GRAPH = {
    ("D", "J2", "Computer Science"): [
        "Students will be able to design, develop, test, deploy and evaluate modern, responsive and accessible websites by using semantic HTML to create well-structured, meaningful and search-engine-friendly documents, and CSS to implement maintainable layouts and visual systems through mobile-first responsive design, Flexbox, CSS Grid, custom properties, media queries and component-based styling conventions, while applying accessibility best practices such as appropriate landmark elements, ARIA roles and attributes where necessary, keyboard navigation, focus management, colour-contrast compliance and screen-reader-friendly content. They will use JavaScript ES6+ to add interactivity and handle asynchronous data, demonstrating competence in variables, functions, modules, array and object manipulation, DOM selection and manipulation, event handling and delegation, form validation and user feedback, error handling with try/catch, promises and async/await, fetching and processing data from external APIs, managing loading and error states, and using browser storage such as localStorage where appropriate. Learners will apply Bootstrap to accelerate the creation of consistent and responsive user interfaces by customising its grid system, spacing utilities, typography and components, overriding default variables and styles to maintain a coherent visual identity, and ensuring that Bootstrap-based interfaces remain accessible and responsive across devices. They will use React to build reusable component-based interfaces with state management through hooks such as useState, useEffect, useContext and useReducer, managing component lifecycle and side effects, lifting state where necessary, passing data through props, handling events and forms in a controlled manner, conditionally rendering UI, composing components into modular and maintainable file structures, and applying basic testing and debugging practices. Learners will employ Next.js to implement routing and appropriate rendering strategies, including Static Site Generation (SSG), Server-Side Rendering (SSR), Incremental Static Regeneration (ISR) and Client-Side Rendering (CSR), selecting strategies according to content dynamism and performance requirements, while applying basic SEO optimisation through metadata management, semantic markup, sitemap and robots considerations, image optimisation using the Next.js Image component, font optimisation, code splitting and performance best practices. Finally, they will use Netlify to build and deploy applications automatically to a public domain through Git repository integration, configuring build commands and publish directories, managing environment variables, redirects and rewrites, integrating basic serverless functions where required, using deploy previews and rollbacks, and applying version control with Git and collaborative workflows such as branching, pull requests and code review. Throughout the process, learners will demonstrate systematic problem-solving, document their design and development decisions, evaluate the usability, accessibility, performance and security of their deployed applications, and consider ethical, social and professional responsibilities in the creation and publication of web-based solutions.",
    ],
    ("D", "J3", "Computer Science"):[
        "Students will be able to apply Design Thinking as a structured, human-centred approach to problem-solving by empathising with users through interviews and observations, defining problems clearly using tools such as personas and journey maps, generating and evaluating ideas through divergent and convergent thinking, and building low-fidelity and high-fidelity prototypes that are tested and iterated based on user feedback. They will explain and perform operations on binary number systems, including conversion between binary, decimal, octal and hexadecimal, binary arithmetic (addition, subtraction and multiplication), representation of signed and unsigned integers, and the basic principles of floating-point representation. Learners will describe the fundamentals of computer networks, including network topologies (bus, star, ring, mesh), transmission media, common network devices, the OSI and TCP/IP reference models, IP addressing and subnetting, and core protocols such as HTTP, DNS, DHCP and TCP/UDP, as well as apply basic troubleshooting techniques. They will explain the organisation and architecture of computer systems, including the von Neumann architecture, CPU components (ALU, control unit, registers), the instruction cycle, pipelining, memory hierarchy (registers, cache, RAM, secondary storage), input/output mechanisms, and the distinction between RISC and CISC architectures. Learners will write basic C++ programs using variables, data types, operators, control structures (sequence, selection and iteration), functions, arrays, basic pointers, file input/output and modular programming practices, while applying debugging techniques and adhering to good coding conventions. They will design database entity-relationship diagrams (ERDs) by identifying entities, attributes and relationships, specifying cardinality and participation constraints, recognising weak entities and associative entities, applying normalisation principles up to the third normal form (3NF), and mapping ERDs to relational schemas. Throughout, learners will demonstrate logical reasoning, systematic problem-solving, collaboration and effective communication of technical solutions, and will consider ethical, social and professional responsibilities in the design and use of computing systems."
    ],
    ("D", "J1", "Health and Physical Education"):[
        "At the end of Phase D, students are projected to be able to practise the analysis of specific movement skills, carry out fitness training in accordance with established principles, and prioritise personal and social responsibility, and broadly, the Physical Education, Sport, and Health (PJOK) learning outcomes for junior high school are divided into four main elements, namely movement skills, which involve practising the results of specific movement analysis covering games and sports such as invasion, net, and field games, gymnastics, rhythmic movement, and water sports, movement knowledge, which involves understanding, analysing, and evaluating the concepts and strategies of various physical activities, movement utilisation, which involves improving physical fitness related to both health and skills and understanding the prevention of non-communicable diseases, and character development, which involves demonstrating cooperation, fair play values, and independence in monitoring personal fitness."
    ],
    ("D", "J2", "Health and Physical Education"):[
        "At the end of Phase D, students are projected to be able to practise the analysis of specific movement skills, carry out fitness training in accordance with established principles, and prioritise personal and social responsibility, and broadly, the Physical Education, Sport, and Health (PJOK) learning outcomes for junior high school are divided into four main elements, namely movement skills, which involve practising the results of specific movement analysis covering games and sports such as invasion, net, and field games, gymnastics, rhythmic movement, and water sports, movement knowledge, which involves understanding, analysing, and evaluating the concepts and strategies of various physical activities, movement utilisation, which involves improving physical fitness related to both health and skills and understanding the prevention of non-communicable diseases, and character development, which involves demonstrating cooperation, fair play values, and independence in monitoring personal fitness."
    ],
    ("E", "S1", "Health and Physical Education"):[
        "At the end of phase E, students focus on evaluating, applying and refining movement skills and healthy lifestyle behaviours, and broadly, the Phase E learning outcomes are divided into four main elements, namely movement skills, in which students are able to design, apply, refine and develop movement strategies in various challenging situations through varied activities such as games, athletics, gymnastics, rhythmic movement and water sports, movement knowledge, in which students analyse the impact of applying movement concepts on skills and understand scientific facts, mechanical principles and tactical strategies in sport, movement utilisation, in which students evaluate the impact of physical activity on fitness and health and apply biomotor training and healthy lifestyle practices, and character and movement values development, in which students demonstrate fair play, ethical behaviour, leadership, collaboration and resilience in facing training and competition pressure."
    ],
    ("E", "S1", "Computer Science"):[
        "Students will be able to use Google Colab as a cloud-based computational environment to write, execute, debug and document Python code for end-to-end data science workflows, including organising notebooks with Markdown documentation, installing and managing third-party libraries, mounting Google Drive for persistent storage, importing and exporting data from local and cloud sources, using GPU and TPU runtimes where appropriate, and collaborating in real time through shared notebooks, comments and version history; collect data systematically from multiple sources by performing web scraping using libraries such as Requests, BeautifulSoup, Scrapy and Selenium to extract data from static and dynamically rendered web pages while handling pagination, rate limiting and session management, and by collecting data through public APIs with authentication, JSON and XML response handling and rate-limit management, as well as through file-based sources such as CSV, Excel, JSON and SQL databases and open data portals, while respecting legal and ethical considerations including robots.txt protocols, terms of service, copyright, data privacy regulations such as GDPR principles, consent and anonymisation of personal data; clean and prepare raw data for analysis by identifying and handling missing values through deletion, imputation or interpolation, removing duplicate records, detecting and treating outliers using statistical and visual methods, standardising inconsistent formats such as dates, currencies and text encodings, converting data types appropriately, normalising and scaling numerical features, encoding categorical variables, and correcting structural errors such as misaligned columns and inconsistent naming conventions; modify and transform data using pandas and NumPy through filtering, sorting, merging, joining, concatenating and reshaping datasets, grouping and aggregating data with pivot tables and groupby operations, creating derived features and calculated columns, applying window functions and time-series transformations, and restructuring data between wide and long formats to suit analytical needs; perform exploratory data analysis by computing descriptive statistics, examining distributions, identifying correlations and patterns and formulating initial hypotheses, and create meaningful and accurate data visualisations using Matplotlib, Seaborn and Plotly by selecting appropriate chart types for different data and analytical purposes, applying principles of clarity, accuracy, labelling and accessibility, customising visual elements such as colours, scales and annotations, and constructing multi-panel and interactive visualisations to communicate insights effectively; and apply foundational data science concepts and methods—including descriptive and inferential statistics, correlation and regression analysis, basic hypothesis testing and introductory predictive modelling using libraries such as scikit-learn—to derive evidence-based insights and support decision-making, communicate findings through well-documented notebooks, structured reports and visual narratives, evaluate the quality, limitations, biases and ethical implications of their data and results, ensure reproducibility through clear documentation of code, data sources and analytical decisions, and demonstrate systematic problem-solving, critical thinking and effective communication of data-driven conclusions in individual and collaborative settings.They will design, implement and evaluate AI agents to automate and augment data science workflows—including agent-based data collection, cleaning, analysis and visualisation—using appropriate frameworks and tools while assessing their reliability, limitations and ethical implications."
    ],
    ("F", "S2", "Health and Physical Education"):[
        "At the end of this phase F, students focus on three main elements of skill and character development, namely moving skilfully, in which they evaluate specific movement skills and strategies to improve performance in various challenging situations, learning through movement, in which they apply and evaluate movement strategies in new situations, uphold fair play, and reflect on the influence of ethical behaviour on physical activity, and evaluate decision-making strategies in teamwork involving leadership and collaboration, and living an active lifestyle, in which they actively participate in fitness activities and evaluate the impact and effectiveness of their strategies on long-term health."
    ],
    ("F", "S2", "Computer Science"): [
        "Students will be able to explain the foundational concepts, scope and societal implications of artificial intelligence and apply machine learning workflows—including problem framing, data preparation, feature engineering, model selection, training, evaluation and interpretation—by distinguishing and implementing supervised learning models for classification and regression tasks using appropriate algorithms such as logistic regression, decision trees, random forests, support vector machines, k-nearest neighbours and linear regression, and unsupervised learning models such as clustering and dimensionality reduction using k-means, hierarchical clustering and principal component analysis; they will build, train and evaluate deep learning models using neural networks, including feedforward networks, convolutional neural networks and recurrent networks where appropriate, applying techniques such as activation functions, loss functions, optimisers, regularisation, dropout and hyperparameter tuning, and will evaluate model performance using suitable metrics including accuracy, precision, recall, F1-score, confusion matrices, mean absolute error, mean squared error, R-squared and cross-validation; they will apply natural language processing models and techniques—including text preprocessing, tokenisation, stemming and lemmatisation, stop-word removal, bag-of-words and TF-IDF representations, word embeddings, sentiment analysis and basic sequence modelling—to process and analyse textual data; and they will interpret results, assess model limitations such as overfitting, bias and data leakage, consider ethical, legal and social implications including privacy, fairness and transparency, communicate findings through structured documentation and visualisations, and demonstrate systematic problem-solving, critical thinking and responsible practice in individual and collaborative projects.",
    ],
    # Tambahkan entri lain sesuai kebutuhan.
}


def get_cp(phase, class_level, subject):
    key = (
        str(phase).strip().upper(),
        str(class_level).strip().upper(),
        str(subject).strip(),
    )
    return list(CP_GRAPH.get(key, []))


# ---------------------------------------------------------
# Parser & normalizer JSON
# ---------------------------------------------------------
def _parse_json(text: str):
    """Ekstrak & parse JSON dari respons Claude (boleh ada ```json fence)."""
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


def _as_str(v):
    return "" if v is None else str(v).strip()


def _as_list(v):
    if isinstance(v, list):
        return v
    if v in (None, ""):
        return []
    return [v]


def _as_dict(v):
    return v if isinstance(v, dict) else {}


def _normalize(parsed: dict, meetings_list: list):
    """Pastikan schema seragam, isi field yang hilang dengan default."""
    parsed = _as_dict(parsed)
    parsed_meets = _as_list(parsed.get("meetings", []))

    meetings = []
    for i, m in enumerate(meetings_list):
        pm = _as_dict(parsed_meets[i]) if i < len(parsed_meets) else {}

        objectives = [_as_str(o) for o in _as_list(pm.get("objectives", [])) if _as_str(o)]

        stages = []
        for st in _as_list(pm.get("stages", [])):
            st = _as_dict(st)
            stages.append({
                "stage": _as_str(st.get("stage", "")),
                "activity": _as_str(st.get("activity", "")),
                "values": _as_str(st.get("values", "")),
            })

        meetings.append({
            "number": m["number"],
            "topic": _as_str(pm.get("topic", "")) or _as_str(m.get("topic", "")),
            "day_date": m.get("date", ""),
            "level": m.get("level", ""),
            "objectives": objectives,
            "stages": stages,
        })

    kv = []
    for v in _as_list(parsed.get("key_vocabulary", [])):
        v = _as_dict(v)
        kv.append({
            "jp": _as_str(v.get("jp", v.get("word", v.get("term", "")))),
            "romaji": _as_str(v.get("romaji", v.get("pronunciation", ""))),
            "arti": _as_str(v.get("arti", v.get("meaning", ""))),
        })

    si = _as_dict(parsed.get("subject_integration", {}))
    si_subjects = []
    for x in _as_list(si.get("subjects", [])):
        x = _as_dict(x)
        si_subjects.append({
            "subject": _as_str(x.get("subject", "")),
            "connection": _as_str(x.get("connection", "")),
            "daily_life": _as_str(x.get("daily_life", "")),
        })

    cb = {
        _as_str(k): _as_str(v)
        for k, v in _as_dict(parsed.get("character_building", {})).items()
    }

    return {
        "learning_outcomes": _as_str(parsed.get("learning_outcomes", "")),
        "prior_knowledge": [_as_str(x) for x in _as_list(parsed.get("prior_knowledge", [])) if _as_str(x)],
        "guiding_questions": [_as_str(x) for x in _as_list(parsed.get("guiding_questions", [])) if _as_str(x)],
        "enduring_understanding": _as_str(parsed.get("enduring_understanding", "")),
        "key_vocabulary": kv,
        "resources_materials": [_as_str(x) for x in _as_list(parsed.get("resources_materials", [])) if _as_str(x)],
        "subject_integration": {"subjects": si_subjects},
        "character_building": cb,
        "meetings": meetings,
        "assessment_reflection": _as_str(parsed.get("assessment_reflection", "")),
    }


# ---------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------
def build_modul_prompt(*, teacher, subject, class_level, phase, duration, term,
                       meetings, reference_text="", cp_list=None):
    cp_list = cp_list or []

    meeting_lines = "\n".join(
        f"- Meeting {m['number']}: {m.get('topic', '').strip() or '(tanpa topik)'} "
        f"| Level Kognitif: {m.get('level', '')} | Tanggal: {m.get('date', '')}"
        for m in meetings
    )
    cp_block = "\n".join(f"{i+1}. {cp}" for i, cp in enumerate(cp_list)) or "(belum ada CP)"
    ref_block = reference_text.strip() or "(tidak ada referensi tambahan)"

    schema = """{
  "learning_outcomes": "string",
  "prior_knowledge": ["string", "..."],
  "guiding_questions": ["string", "..."],
  "enduring_understanding": "string",
  "key_vocabulary": [{"jp": "term", "romaji": "romanization", "arti": "meaning"}],
  "resources_materials": ["string", "..."],
  "subject_integration": {
    "subjects": [
      {"subject": "...", "connection": "...", "daily_life": "..."}
    ]
  },
  "character_building": {"Dimensi": "Deskripsi"},
  "meetings": [
    {
      "topic": "string",
      "objectives": ["string", "..."],
      "stages": [
        {"stage": "Finding Out", "activity": "...", "values": "..."},
        {"stage": "Sorting Out", "activity": "...", "values": "..."},
        {"stage": "Going Further", "activity": "...", "values": "..."},
        {"stage": "Making Connections", "activity": "...", "values": "..."},
        {"stage": "Taking Action", "activity": "...", "values": "..."}
      ]
    }
  ],
  "assessment_reflection": "string"
}"""

    return f"""Anda adalah perancang kurikulum berpengalaman. Buatkan **satu Modul Ajar** lengkap dalam format **JSON valid** (tanpa teks lain di luar JSON).

# IDENTITAS MODUL
- Guru: {teacher}
- Mata Pelajaran: {subject}
- Kelas / Fase: {class_level} / Fase {phase}
- Durasi per meeting: {duration}
- Term / Semester: {term}

# CAPAIAN PEMBELAJARAN (CP)
{cp_block}

# MEETINGS
{meeting_lines}

# REFERENSI TAMBAHAN
{ref_block}

# INSTRUKSI KELUARAN
1. Hasilkan **JSON valid** saja (boleh dibungkus ```json ... ```).
2. Ikuti schema persis berikut:
{schema}
3. `meetings` harus berisi tepat {len(meetings)} item, urut sesuai daftar MEETINGS di atas.
4. Setiap meeting WAJIB punya 5 stages berurutan: Finding Out, Sorting Out, Going Further, Making Connections, Taking Action.
5. Bahasa: Bahasa Indonesia (kecuali `jp`/`romaji` bila mata pelajaran bahasa asing).
6. Jangan tambahkan komentar, penjelasan, atau teks di luar JSON.
"""