"""Study notes, video links and phase-test questions for the improve plan.

Notes are short, curated points for the most common skills. Other skills get notes built
from their category. Video links are YouTube search links, not specific video IDs: a
search always works, and the learner picks a video. A curated video ID would need checking
against YouTube, which this project does not do automatically.
"""
from urllib.parse import quote_plus

from app.services.mock_content import MCQ_BANK

NOTES = {
    "python": [
        "Everything is an object. Lists, dicts and tuples are the containers you will use daily.",
        "Use list comprehensions for simple transforms and plain loops when the logic is complex.",
        "Write functions that take inputs and return values, and avoid relying on global state.",
    ],
    "sql": [
        "SELECT picks columns, WHERE filters rows, GROUP BY aggregates, HAVING filters groups.",
        "JOIN combines tables. INNER keeps matches, LEFT keeps every row from the left table.",
        "An index speeds up lookups and sorting, but slows writes and takes space.",
    ],
    "javascript": [
        "let and const are block scoped. Prefer const, and use let only when you reassign.",
        "Promises and async/await handle work that finishes later, such as network calls.",
        "map returns a new array, filter keeps matches, reduce folds the array into one value.",
    ],
    "typescript": [
        "Types are checked at compile time and removed at run time.",
        "Use interfaces for object shapes and unions for values that can be one of several types.",
        "Avoid any. It switches the checks off, which defeats the purpose.",
    ],
    "react": [
        "A component is a function that returns what to show for its current props and state.",
        "Put state in the lowest component that needs it, and pass data down through props.",
        "useEffect runs after render. Return a cleanup function for subscriptions and timers.",
    ],
    "node.js": [
        "Node runs JavaScript on the server and handles many requests with one event loop.",
        "Keep blocking work out of request handlers. Move slow work to a queue or a worker.",
        "Read configuration from environment variables, never from code.",
    ],
    "fastapi": [
        "Type hints on parameters drive validation and the automatic API docs.",
        "Dependencies (Depends) share logic such as the current user or a database session.",
        "Use the built-in test client to test endpoints without starting a server.",
    ],
    "html": [
        "Use semantic elements (main, nav, section, article) so screen readers and search engines understand the page.",
        "Every form input needs a label. Every image needs alt text.",
        "Structure first, style second. Keep HTML meaningful even with CSS turned off.",
    ],
    "css": [
        "Flexbox lays out one row or column. Grid lays out rows and columns together.",
        "The box model: content, padding, border, margin. box-sizing: border-box makes widths predictable.",
        "Use media queries or fluid units so the layout works from phone to desktop.",
    ],
    "git": [
        "A commit is a snapshot. A branch is a movable pointer to a commit.",
        "Pull, review and merge in small steps. Commit messages should say why, not only what.",
        "git stash saves unfinished work so you can switch branches safely.",
    ],
    "docker": [
        "An image is a read-only template. A container is a running copy of an image.",
        "Order Dockerfile steps so dependencies install before your code, to use the cache.",
        "Use volumes for data that must survive when a container is replaced.",
    ],
    "ci/cd": [
        "Continuous integration runs tests on every push. Continuous delivery prepares a release every time.",
        "A failing test should stop the pipeline before anything is deployed.",
        "Keep secrets in the CI provider's secret store, never in the repository.",
    ],
    "aws": [
        "IAM decides who can do what. Give each role only the permissions it needs.",
        "S3 stores files, EC2 runs virtual servers, Lambda runs functions without servers.",
        "Set a billing alert before you create anything, so surprises are caught early.",
    ],
    "postgresql": [
        "Declare primary and foreign keys so the database enforces relationships.",
        "A transaction groups statements that must succeed or fail together.",
        "EXPLAIN ANALYZE shows how a query actually runs. Read it before adding indexes.",
    ],
    "machine learning": [
        "Split data into training, validation and test sets before you look at results.",
        "A model that scores well on training data but poorly on new data is overfitting.",
        "Pick metrics that match the problem. Accuracy misleads when classes are imbalanced.",
    ],
    "pandas": [
        "A DataFrame is a table. Columns are Series, and most operations return a new DataFrame.",
        "Decide what to do with missing values on purpose: drop, fill, or flag them.",
        "groupby splits data into groups, then aggregates each group.",
    ],
    "numpy": [
        "An ndarray holds values of one type in a fixed shape. Shape tells you its dimensions.",
        "Vectorised operations run on whole arrays in compiled code, far faster than Python loops.",
        "Broadcasting lets arrays of different shapes combine when their dimensions are compatible.",
    ],
    "data analysis": [
        "Start from the question. The question decides which data, measure and chart you need.",
        "Check the data before you trust it: counts, missing values, and outliers.",
        "A good conclusion states the finding, the number behind it, and what it does not show.",
    ],
    "redis": [
        "Redis keeps data in memory, so reads are very fast. Use it for caching and counters.",
        "Set a TTL on cached keys so stale data expires on its own.",
        "A cache miss should fall back to the database and then store the result.",
    ],
    "linux": [
        "Everything is a file. Permissions are read, write and execute for owner, group and others.",
        "The shell pipes one command's output into another with |, and redirects with > and >>.",
        "Learn grep, find, ps, top and systemctl. They cover most troubleshooting.",
    ],
    "kubernetes": [
        "A Pod is the smallest unit, usually one container. Deployments keep the right number of Pods running.",
        "Services give Pods a stable address. Ingress routes outside traffic to them.",
        "Describe the desired state in YAML and let Kubernetes reconcile towards it.",
    ],
    "terraform": [
        "Describe infrastructure in code. terraform plan shows what will change before terraform apply does it.",
        "State records what Terraform created. Keep it in a shared, locked backend for teams.",
        "Use modules to reuse infrastructure patterns across projects.",
    ],
    "cybersecurity": [
        "Confidentiality, integrity and availability are the core goals of security.",
        "Least privilege: give every account only the access it needs.",
        "Patch regularly and log enough to investigate an incident afterwards.",
    ],
    "generative ai": [
        "A generative model produces new text, images or code by predicting likely continuations.",
        "Models can be confidently wrong. Check important output against a source.",
        "Retrieval-augmented generation feeds the model relevant documents before it answers.",
    ],
    "prompt engineering": [
        "State the role, the task, the context and the output format explicitly.",
        "Give one or two examples of the output you want. This is few-shot prompting.",
        "Iterate: change one part of the prompt, compare outputs, and keep what works.",
    ],
    "excel": [
        "Use tables and named ranges so formulas stay readable when data grows.",
        "XLOOKUP or INDEX/MATCH find values. PivotTables summarise large data quickly.",
        "Keep raw data separate from calculations and charts.",
    ],
    "power bi": [
        "Load data, model the relationships, then build visuals. Do the cleaning in Power Query.",
        "Measures (DAX) calculate values on the fly. Calculated columns are stored with the data.",
        "A dashboard should answer one business question per visual.",
    ],
    "selenium": [
        "Find elements with stable locators, such as IDs or data attributes, not fragile XPaths.",
        "Use explicit waits for elements to appear, instead of fixed sleeps.",
        "Keep each test independent so one failure does not cascade.",
    ],
    "figma": [
        "Components and variants keep designs consistent. Change the component and every copy updates.",
        "Auto layout makes frames resize the way a real screen would.",
        "Prototype the main flow before polishing every screen.",
    ],
    "agile": [
        "Work in short cycles, deliver something usable each time, and inspect the result.",
        "A backlog is ordered by value. The top items are small enough to finish in one cycle.",
        "Retrospectives are where the team changes how it works, not only what it builds.",
    ],
    "communication": [
        "Lead with the answer, then give the reasoning and the evidence.",
        "Restate what you heard to confirm you understood before you respond.",
        "Match the detail to the audience: a manager needs the outcome, an engineer needs the mechanism.",
    ],
    "flutter": [
        "Everything in Flutter is a widget. Compose small widgets rather than writing large ones.",
        "setState rebuilds the widget that owns the state. Keep state close to where it is used.",
        "Use hot reload to see changes in a second while you build screens.",
    ],
    "tailwind css": [
        "Utility classes style elements directly. Compose them in the markup instead of writing new CSS.",
        "Use responsive prefixes like md: to change layouts at breakpoints.",
        "Extract a component when the same class list repeats, rather than copying classes.",
    ],
}

GENERIC_NOTES = {
    "Programming Language": "Read the official tutorial for the first chapters, then solve small problems in it.",
    "Framework": "Build one small app with the framework, following its official guide, then change it on purpose.",
    "Database": "Learn the core operations, then practise on a real dataset and read the query plans.",
    "Cloud/DevOps": "Learn the core services and the security model first. Practise in a free tier and tear everything down.",
    "Data/ML": "Work through a short course, then reproduce one public analysis or model and explain each step.",
    "Testing": "Write a few tests for one of your own projects first. Good tests come from practice, not from reading.",
    "Project & Product": "Practise on a small real project: write the artefact, review it with someone, and revise it.",
    "Design": "Study two or three good examples closely, then redo one of them yourself.",
    "Security": "Learn the threat model first, then practise on a legal lab environment, never on systems you do not own.",
    "Soft Skill": "Practise deliberately: prepare a short example from your own experience and say it out loud.",
    "Computer Science": "Solve a few problems by hand before you code them. The reasoning matters more than the syntax.",
    "Marketing": "Run one small experiment, measure the result, and write down what you learned.",
    "Emerging": "Build one small working example, then read the primary sources for the details.",
}


def youtube_search_url(query: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(query)


def notes_for(skill: str, category: str | None) -> list[str]:
    key = skill.lower()
    if key in NOTES:
        return NOTES[key]
    fallback = GENERIC_NOTES.get(category or "", "Study the official documentation, then practise with a small project.")
    return [fallback, f"Focus on the core concepts of {skill} before the advanced topics."]


def videos_for_task(skill: str, task_text: str) -> list[dict]:
    """Two search links per task: one for the specific task, one for a full course on the skill."""
    short = task_text.split(" ")[:6]
    return [
        {"title": f"Find a video: {' '.join(short)}", "url": youtube_search_url(f"{skill} {' '.join(short)}")},
        {"title": f"Full {skill} course", "url": youtube_search_url(f"{skill} full course for beginners")},
    ]


# ---------- phase tests ----------

# Used when a phase's skills have too few multiple-choice questions of their own.
GENERAL_POOL = [
    {"id": "g-1", "skill": "software", "question": "Which HTTP status code means the resource was not found?",
     "options": ["200", "301", "404", "500"], "answer": 2},
    {"id": "g-2", "skill": "software", "question": "What does Big-O notation describe?",
     "options": ["The exact run time in seconds", "How run time grows as input grows",
                 "The size of the code file", "The number of developers"], "answer": 1},
    {"id": "g-3", "skill": "software", "question": "Which Git command saves a snapshot of staged changes?",
     "options": ["git commit", "git clone", "git fetch", "git tag"], "answer": 0},
    {"id": "g-4", "skill": "software", "question": "Why write automated tests?",
     "options": ["To slow down releases", "To catch regressions when code changes",
                 "To replace documentation", "To remove the need for review"], "answer": 1},
    {"id": "g-5", "skill": "software", "question": "What does an API contract describe?",
     "options": ["The office a team works in", "The inputs, outputs and errors of an interface",
                 "The database password", "The colour scheme"], "answer": 1},
    {"id": "g-6", "skill": "software", "question": "Which practice keeps secrets out of source code?",
     "options": ["Committing a .env file", "Storing them in environment variables or a secret store",
                 "Putting them in comments", "Printing them in logs"], "answer": 1},
    {"id": "g-7", "skill": "software", "question": "What is the main purpose of code review?",
     "options": ["To count lines of code", "To share knowledge and catch defects early",
                 "To assign blame", "To delay merges"], "answer": 1},
    {"id": "g-8", "skill": "software", "question": "Which is a good reason to add an index to a database column?",
     "options": ["The column is rarely searched", "The column is often used in WHERE clauses",
                 "The column has many NULLs", "The column is never sorted"], "answer": 1},
]

PHASE_TEST_SIZE = 5
PHASE_PASS_SCORE = 60  # percent


def phase_test_questions(skills: list[str], seed: int) -> list[dict]:
    """Questions for one phase test: this phase's own questions first, then general ones.

    Deterministic for a given seed, so a reload shows the same questions.
    """
    wanted = {s.lower() for s in skills}
    own = [q for q in MCQ_BANK if q["skill"] in wanted]
    try:
        from app.services.daily_bank import DAILY_BANK
        own += [q for q in DAILY_BANK if q.get("kind", "mcq") == "mcq" and q["skill"] in wanted]
    except ImportError:  # the daily bank is optional for this helper
        pass
    seen, unique = set(), []
    for q in own:
        if q["id"] not in seen:
            seen.add(q["id"])
            unique.append(q)
    rotated = unique[seed % len(unique):] + unique[:seed % len(unique)] if unique else []
    chosen = rotated[:PHASE_TEST_SIZE]
    for q in GENERAL_POOL:
        if len(chosen) >= PHASE_TEST_SIZE:
            break
        chosen.append(q)
    return [dict(q, kind="mcq") for q in chosen[:PHASE_TEST_SIZE]]


def grade_phase_test(questions: list[dict], answers: dict) -> dict:
    correct = sum(1 for q in questions if answers.get(q["id"]) == q["answer"])
    total = len(questions) or 1
    score = round(100 * correct / total, 1)
    return {"score": score, "correct": correct, "total": len(questions), "passed": score >= PHASE_PASS_SCORE}
