"""The AI interviewer.

A conversation, not a quiz: it asks an opening question, scores each answer against what a
strong answer for that skill covers, and follows up on the gaps. It ends after a set number
of turns with a report.

Two engines, same behaviour:
  - Rule-based (always available): scores by coverage of expected points and by how concrete
    the answer is (examples, numbers, "I"). Follow-ups name the point that was missing.
  - Language model (when ANTHROPIC_API_KEY is set): wording, follow-ups and feedback come from
    the model. If the model's reply cannot be read, the rule-based engine is used for that turn.
"""
import json
import re

from app.services.llm import complete, llm_available
from app.services.mock_content import ROLE_SKILLS

TARGET_TURNS = 5
FOLLOW_UP_BELOW = 55  # an answer scoring under this gets one follow-up on its gap
CONCRETE_MARKERS = re.compile(r"\b(for example|for instance|i built|i designed|i led|i fixed|i reduced|i improved|"
                              r"result|because|measured|by \d+|\d+%|\d+ (users|requests|seconds|ms|hours))\b", re.I)

# What a strong answer covers, per skill. Keywords are matched case-insensitively.
SKILL_QUESTIONS = {
    "python": ("How do you decide between a list, a dict and a set in Python?", ["list", "dict", "set", "lookup", "unique", "order"]),
    "sql": ("How would you find the top three customers by revenue in a sales table?", ["group by", "order by", "limit", "sum", "join"]),
    "javascript": ("Explain how asynchronous code runs in JavaScript.", ["event loop", "promise", "async", "await", "callback"]),
    "typescript": ("When would you use an interface instead of a type alias in TypeScript?", ["interface", "type", "extend", "union", "object"]),
    "react": ("How do you decide what state belongs in a component, and what belongs in props?", ["state", "props", "lift", "re-render", "child"]),
    "node.js": ("How do you keep a Node.js API responsive when a request needs slow work?", ["event loop", "queue", "worker", "async", "block"]),
    "fastapi": ("How does FastAPI validate a request body, and what happens when it fails?", ["pydantic", "validation", "422", "model", "type"]),
    "docker": ("What is the difference between a Docker image and a container?", ["image", "container", "layer", "run", "template"]),
    "git": ("How do you resolve a merge conflict?", ["conflict", "merge", "markers", "commit", "resolve"]),
    "aws": ("How would you give an application access to an S3 bucket securely?", ["iam", "role", "policy", "least privilege", "s3"]),
    "postgresql": ("When would an index help a query, and when would it hurt?", ["index", "write", "lookup", "explain", "space"]),
    "machine learning": ("How do you tell whether a model is overfitting?", ["train", "validation", "test", "gap", "overfit"]),
    "pandas": ("How do you handle missing values in a DataFrame?", ["dropna", "fillna", "missing", "isnull", "decide"]),
    "data analysis": ("Walk me through how you would analyse a dataset you had never seen.", ["question", "clean", "explore", "chart", "conclusion"]),
    "kubernetes": ("What happens when a Pod crashes in a Kubernetes deployment?", ["restart", "deployment", "replica", "pod", "controller"]),
    "terraform": ("How do you avoid losing track of what Terraform has created?", ["state", "plan", "backend", "lock", "module"]),
    "linux": ("How would you find which process is using a port?", ["lsof", "ss", "netstat", "port", "pid"]),
    "cybersecurity": ("How would you limit the damage if a user account is compromised?", ["least privilege", "mfa", "log", "revoke", "monitor"]),
    "generative ai": ("What are the main risks of using a generative model in a product?", ["hallucination", "wrong", "bias", "verify", "privacy"]),
    "prompt engineering": ("How do you improve a prompt that gives inconsistent answers?", ["example", "format", "role", "context", "iterate"]),
    "excel": ("How would you summarise sales by region in a large sheet?", ["pivot", "sumif", "table", "group", "filter"]),
    "power bi": ("How do you decide what to show on a dashboard?", ["question", "measure", "visual", "audience", "filter"]),
    "communication": ("Tell me about a time you explained something technical to a non-technical person.", ["example", "simple", "listen", "result", "checked"]),
    "teamwork": ("Describe a disagreement with a teammate and how you resolved it.", ["listened", "agreed", "resolved", "result", "team"]),
    "problem solving": ("Describe a hard problem you solved and how you approached it.", ["problem", "approach", "tried", "root cause", "result"]),
    "leadership": ("When have you taken ownership of something without being asked?", ["ownership", "decided", "team", "result", "plan"]),
    "agile": ("How does a sprint work, and what do you do in the retrospective?", ["sprint", "backlog", "retrospective", "review", "cycle"]),
    "figma": ("How do you use components so a design stays consistent?", ["component", "variant", "auto layout", "consistent", "update"]),
    "ui/ux design": ("How do you decide whether a design is working for users?", ["user", "test", "feedback", "task", "usability"]),
    "selenium": ("How do you keep UI tests from becoming flaky?", ["wait", "locator", "independent", "stable", "retry"]),
    "flutter": ("How does state management work in a Flutter app?", ["state", "widget", "setstate", "rebuild", "provider"]),
}
GENERIC_KEYWORDS = ["project", "built", "problem", "result", "because"]


def _question_for(skill: str) -> tuple[str, list[str]]:
    if skill.lower() in SKILL_QUESTIONS:
        return SKILL_QUESTIONS[skill.lower()]
    return (f"Describe a project where you used {skill}. What was your part, and what was the result?", GENERIC_KEYWORDS)


def start_state(role: str) -> dict:
    if role not in ROLE_SKILLS:
        raise ValueError("Unknown role")
    skills = [s for s in ROLE_SKILLS[role]]
    return {
        "role": role,
        "target_turns": TARGET_TURNS,
        "skills": skills,
        "turns": [],
        "pending_follow_up": None,
    }


def _opening(role: str) -> dict:
    return {"kind": "opening", "skill": None,
            "question": f"Hi, I'm your interviewer for the {role} role. To begin, tell me about yourself and the piece of work you are most proud of.",
            "keywords": []}


def first_question(state: dict) -> dict:
    return _opening(state["role"])


def score_answer(answer: str, keywords: list[str]) -> dict:
    text = (answer or "").lower()
    words = len(text.split())
    matched = [k for k in keywords if k.lower() in text]
    missing = [k for k in keywords if k.lower() not in text]
    coverage = len(matched) / len(keywords) if keywords else 0.5
    concrete = 1.0 if CONCRETE_MARKERS.search(text) else 0.0
    length = min(1.0, words / 60)
    score = round(100 * (0.55 * coverage + 0.25 * concrete + 0.20 * length), 1)
    return {"score": score, "matched": matched, "missing": missing, "words": words, "concrete": bool(concrete)}


def _feedback(result: dict) -> str:
    parts = []
    if result["score"] >= 75:
        parts.append("That was a strong answer.")
    elif result["score"] >= 50:
        parts.append("A solid answer with room to go deeper.")
    else:
        parts.append("The answer needs more substance.")
    if result["matched"]:
        parts.append("You covered: " + ", ".join(result["matched"][:3]) + ".")
    if not result["concrete"]:
        parts.append("Give one concrete example with a result next time.")
    return " ".join(parts)


def _llm_turn(state: dict, question: str, answer: str, result: dict) -> dict | None:
    system = (
        "You are a friendly, rigorous interviewer for a " + state["role"] + " role. "
        "Reply with JSON only, no prose: {\"feedback\": \"one or two sentences\", "
        "\"follow_up\": \"a single follow-up question, or empty string\"}. "
        "Be specific about what was missing. Never reveal model answers."
    )
    prompt = (f"Question: {question}\nCandidate answer: {answer}\n"
              f"Rule-based score: {result['score']}/100. Points not mentioned: {', '.join(result['missing']) or 'none'}.")
    raw = complete(system, [{"role": "user", "content": prompt}], max_tokens=300)
    if not raw:
        return None
    try:
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        return {"feedback": str(data.get("feedback", "")).strip(), "follow_up": str(data.get("follow_up", "")).strip()}
    except (ValueError, TypeError):
        return None


def answer_turn(state: dict, answer: str) -> dict:
    """Score the answer to the current question, then choose what to ask next."""
    current = state.get("pending_question") or _opening(state["role"])
    keywords = current.get("keywords", [])
    if current["kind"] == "opening":
        result = {"score": 60.0 if len((answer or "").split()) >= 15 else 35.0, "matched": [], "missing": [],
                  "words": len((answer or "").split()), "concrete": bool(CONCRETE_MARKERS.search((answer or "").lower()))}
    else:
        result = score_answer(answer, keywords)

    feedback = _feedback(result) if current["kind"] != "opening" else (
        "Good introduction." if result["score"] >= 50 else "Try to add more about your own work.")
    if llm_available():
        llm = _llm_turn(state, current["question"], answer or "", result)
        if llm and llm.get("feedback"):
            feedback = llm["feedback"]
    state["turns"].append({"question": current["question"], "skill": current.get("skill"),
                           "answer": (answer or "")[:2000], "score": result["score"], "feedback": feedback,
                           "missing": result["missing"]})

    done = len(state["turns"]) >= state["target_turns"]
    if done:
        state["pending_question"] = None
        return {"done": True, "feedback": feedback, "next": None, "report": report(state)}

    # One follow-up on a weak answer, about the point it missed.
    follow = None
    if current["kind"] != "opening" and result["score"] < FOLLOW_UP_BELOW and not state.get("pending_follow_up"):
        missing = result["missing"][0] if result["missing"] else (current.get("skill") or "your approach")
        follow = {"kind": "follow_up", "skill": current.get("skill"),
                  "question": f"Your answer did not cover '{missing}'. Can you add how you would handle it?",
                  "keywords": keywords}
        if llm_available() and state["turns"]:
            llm = _llm_turn(state, current["question"], answer or "", result)
            if llm and llm.get("follow_up"):
                follow["question"] = llm["follow_up"]
        state["pending_follow_up"] = current.get("skill")
    else:
        state["pending_follow_up"] = None

    if follow is None:
        asked = {t.get("skill") for t in state["turns"]}
        remaining = [s for s in state["skills"] if s not in asked]
        skill = remaining[0] if remaining else state["skills"][len(state["turns"]) % len(state["skills"])]
        question, kws = _question_for(skill)
        follow = {"kind": "question", "skill": skill, "question": question, "keywords": kws}

    state["pending_question"] = follow
    return {"done": False, "feedback": feedback, "next": follow, "report": None}


def report(state: dict) -> dict:
    turns = state["turns"]
    scores = [t["score"] for t in turns]
    overall = round(sum(scores) / len(scores), 1) if scores else 0.0
    by_skill: dict[str, list[float]] = {}
    for t in turns:
        if t.get("skill"):
            by_skill.setdefault(t["skill"], []).append(t["score"])
    strengths = [s for s, v in by_skill.items() if sum(v) / len(v) >= 70]
    gaps = [s for s, v in by_skill.items() if sum(v) / len(v) < 50]
    if overall >= 75:
        verdict = "Ready for a first interview round for this role."
    elif overall >= 55:
        verdict = "Close. Practise the gaps below, then try again."
    else:
        verdict = "Not yet. Work through the plan for this role before the next attempt."
    from app.services.interview_dimensions import compute as compute_dimensions
    return {
        "overall": overall,
        "dimensions": compute_dimensions(turns),
        "turns": len(turns),
        "per_skill": {s: round(sum(v) / len(v), 1) for s, v in by_skill.items()},
        "strengths": strengths,
        "gaps": gaps,
        "verdict": verdict,
        "engine": "language model" if llm_available() else "rule-based",
    }
