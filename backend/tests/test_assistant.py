"""Help assistant: answers the questions a user actually asks, without reading any user data."""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_assistant_test_{uuid.uuid4().hex}.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.assistant import faq_answer  # noqa: E402

client = TestClient(app)


def _ask(message):
    return client.post("/assistant/chat", json={"message": message, "history": []}).json()


def test_common_questions_get_the_right_answer():
    assert "phase" in _ask("Why is my phase locked?")["reply"].lower()
    assert "certificates" in _ask("How do I upload several certificates?")["reply"].lower()
    assert "30" in _ask("How is my score calculated?")["reply"]


def test_an_unknown_question_gets_a_helpful_fallback_with_suggestions():
    r = _ask("zzqq xxyy")
    assert r["reply"] and r["suggestions"]


def test_the_assistant_works_without_signing_in_and_reports_its_source():
    r = _ask("How does the AI interview work?")
    assert r["source"] == "faq" and "question" in r["reply"].lower()


def test_an_empty_message_gets_a_greeting():
    assert "SkillDNA helper" in faq_answer("")


def test_long_input_is_capped():
    assert len(_ask("upload " * 500)["reply"]) < 600
