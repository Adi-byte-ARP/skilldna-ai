"""Optional language-model access.

If ANTHROPIC_API_KEY is set, the AI interviewer and the help assistant use the Anthropic
Messages API for wording and feedback. If it is not set, both fall back to their rule-based
engines, so the app works offline and in tests.

Model: ANTHROPIC_MODEL (default below). Nothing is sent unless the key is configured.
"""
import os

import httpx

DEFAULT_MODEL = "claude-haiku-5-5"
API_URL = "https://api.anthropic.com/v1/messages"


def llm_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def complete(system: str, messages: list[dict], max_tokens: int = 500, timeout: float = 20.0) -> str | None:
    """One completion. Returns None when no key is configured or the call fails."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        response = httpx.post(
            API_URL,
            timeout=timeout,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={
                "model": os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
            },
        )
        response.raise_for_status()
        blocks = response.json().get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        return text or None
    except (httpx.HTTPError, ValueError):
        return None
