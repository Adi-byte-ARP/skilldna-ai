"""The help assistant: answers questions about how SkillDNA works.

Answers come from a curated list (always available). When ANTHROPIC_API_KEY is set, the
language model answers from the same facts, so it cannot invent features the app lacks.
The assistant never receives a user's documents, scores or account details.
"""
import re

from app.services.llm import complete, llm_available

FAQ = [
    (["upload", "resume", "pdf"],
     "Upload your resume as a PDF in the Resume card. The name on it must match your account name, "
     "or it is marked and not counted. Uploading the same file again changes nothing."),
    (["certificate", "certificates", "certification", "course"],
     "Upload one or several certificates at once (PNG, JPG, WEBP or PDF). Every file is scanned. "
     "The name on each certificate must match your account, and the skills in its title are counted."),
    (["linkedin", "skills section", "screenshot"],
     "Screenshot your LinkedIn Skills section, or export your profile as a PDF. The file must show your name "
     "so it can be checked. Only the Skills section counts, not the sidebar."),
    (["github", "repo", "repository"],
     "Enter your GitHub username in the GitHub card. Each analysis replaces the previous one, "
     "so repository changes show up when you run it again."),
    (["score", "scoring", "how is my score", "points", "weighted"],
     "Your score combines four sources: resume 30, GitHub 30, LinkedIn 25 and certificates 15. "
     "Skills claimed only on a resume stay below 60 until another source confirms them."),
    (["weak", "gap", "missing", "not shown"],
     "A gap is a skill your target role expects. 'Not shown yet' means no evidence; 'weak' means evidence under 60."),
    (["plan", "improve plan", "roadmap"],
     "The improve plan lists the skills for your target role, with notes, practice tasks and video links "
     "for each task. Tick tasks off as you finish them."),
    (["phase", "locked", "unlock", "next phase"],
     "A phase unlocks the next one. Tick every task in your current phase, then pass its phase test "
     "with at least 60%. You can retake the test."),
    (["daily", "challenge", "streak"],
     "One question a day, with a streak. Most days target your gaps; every third day explores a new skill. "
     "Each day can be answered once."),
    (["mock", "test", "exam", "proctor", "violation"],
     "A mock test is timed and proctored: fullscreen, camera on, and tab changes are recorded. "
     "After two violations the session ends and is scored."),
    (["interview", "ai interview", "interviewer", "voice", "speak"],
     "The AI interviewer asks a question, scores your answer, and follows up on gaps. "
     "Answer by typing or by voice if your browser supports it. It ends with a report."),
    (["password", "gmail", "email", "sign up", "register", "account"],
     "Sign up with a Gmail address. The password needs 8 or more characters with uppercase, lowercase, "
     "a number and a symbol, and must not contain your Gmail name. Gmail dots are ignored, so "
     "a.b@gmail.com and ab@gmail.com are the same account."),
    (["role", "roles", "target role", "career"],
     "Pick a target role to set the skills and the plan. There are 14 roles, from Frontend Developer to "
     "Cybersecurity Analyst. You can change the role at any time."),
    (["reminder", "notification", "email reminder"],
     "Reminders are off until you turn them on. You can get a browser notification or an evening email "
     "on days you have not answered the daily challenge."),
    (["name mismatch", "not counted", "name", "wrong name"],
     "Documents must show the name on your account (first name and surname). A document with a different "
     "name is kept, marked and not counted."),
]

GREETING = ("Hi, I'm the SkillDNA helper. Ask me how uploads, scores, the plan, the mock test or the "
            "AI interview work.")
FALLBACK = ("I don't have an answer for that yet. Try asking about uploads, certificates, scores, "
            "the improve plan, phase tests, the mock test or the AI interview.")
SUGGESTIONS = ["How is my score calculated?", "How do I upload certificates?",
               "Why is a phase locked?", "How does the AI interview work?"]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def faq_answer(question: str) -> str | None:
    q = (question or "").lower()
    if not q.strip():
        return GREETING
    best, best_score = None, 0
    tokens = _tokens(q)
    for keywords, answer in FAQ:
        # Longer, more specific keywords count for more ("certificates" beats "upload").
        score = sum(len(k) for k in keywords if (" " in k and k in q) or (" " not in k and k in tokens))
        if score > best_score:
            best, best_score = answer, score
    return best if best_score > 0 else None


SYSTEM = (
    "You are the SkillDNA helper, a short, friendly guide inside a student skill-assessment app. "
    "Answer in at most three sentences. Use only these facts:\n- " + "\n- ".join(a for _, a in FAQ) +
    "\nIf the question is not about the app, say what you can help with. Never ask for passwords or documents."
)


def answer(question: str, history: list[dict] | None = None, context: dict | None = None) -> dict:
    question = (question or "").strip()[:800]
    if context:
        from app.services.assistant_context import action_reply, intent_for
        intent = intent_for(question)
        if intent:
            done = action_reply(intent, context)
            return {"reply": done["reply"], "source": done["source"], "suggestions": SUGGESTIONS,
                    "data": done.get("data", {})}
    if llm_available() and question:
        messages = [{"role": m["role"], "content": m["content"][:800]} for m in (history or [])[-6:]
                    if m.get("role") in ("user", "assistant") and m.get("content")]
        messages.append({"role": "user", "content": question})
        system = SYSTEM
        if context:
            facts = (f"The user is {context['first_name']}. Target role: {context['role']}. "
                     f"Score {round(context['overall'])}/100 ({context['tier']}). "
                     f"Strengths: {', '.join(context['strengths']) or 'none yet'}. "
                     f"Gaps: {', '.join(context['gaps']) or 'none'}. Streak: {context['streak']} days.")
            system = SYSTEM + "\nUser progress (only share it when relevant): " + facts
        reply = complete(system, messages, max_tokens=300, timeout=15)
        if reply:
            return {"reply": reply, "source": "language model", "suggestions": SUGGESTIONS}
    reply = faq_answer(question)
    if reply is None:
        return {"reply": FALLBACK, "source": "faq", "suggestions": SUGGESTIONS}
    return {"reply": reply, "source": "faq", "suggestions": SUGGESTIONS}
