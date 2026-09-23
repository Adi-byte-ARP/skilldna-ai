"""
GitHub profile analyzer.

Uses the public GitHub REST API (no auth required for basic public data,
though an auth token raises the rate limit from 60 to 5000 req/hr — set
GITHUB_TOKEN in env for production use).

IMPORTANT: this only makes 2 API calls total (user profile + repo list),
not one extra call per repo. Each repo object already includes its
primary language for free — hitting /repos/{owner}/{repo}/languages
separately for every repo burns through the 60/hr unauthenticated quota
almost immediately (a profile with 20 repos = 22 calls = a third of the
hourly budget gone in one click). We trade byte-level language-mix
precision for staying well within rate limits by default.
"""
import os
import re
import requests
from app.utils.skills_taxonomy import ALIAS_LOOKUP, SKILLS_TAXONOMY

GITHUB_API = "https://api.github.com"

USERNAME_JUNK_PATTERN = re.compile(
    r"^\s*(?:https?://)?(?:www\.)?github\.com/|^\s*@|/\s*$", re.IGNORECASE
)


def normalize_username(raw: str) -> str:
    """Accepts a bare username, a full profile URL, an @handle, or any
    combination with stray whitespace/slashes, and returns just the
    username GitHub's API expects. People paste URLs far more often than
    bare usernames, so this needs to be forgiving."""
    value = raw.strip()
    # strip repeatedly in case of "@" + URL combos, then take the first
    # path segment left over
    while True:
        new_value = USERNAME_JUNK_PATTERN.sub("", value).strip()
        if new_value == value:
            break
        value = new_value
    value = value.split("/")[0].split("?")[0].strip()
    return value


def _headers():
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SkillDNA-AI",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _rate_limit_message(resp) -> str:
    remaining = resp.headers.get("x-ratelimit-remaining")
    reset = resp.headers.get("x-ratelimit-reset")
    if remaining == "0" and reset:
        import datetime
        reset_time = datetime.datetime.fromtimestamp(int(reset)).strftime("%H:%M:%S")
        return (
            f"GitHub API rate limit reached (resets at {reset_time} local time). "
            f"This limit is shared by your network/IP, not just this app. "
            f"Set a GITHUB_TOKEN env var (free personal access token from "
            f"github.com/settings/tokens) to raise it from 60 to 5,000 requests/hour."
        )
    return "GitHub API request was forbidden — the request may be missing required headers."


def fetch_github_profile(username: str) -> dict:
    """Fetch repos and their primary languages for a GitHub user.
    Raises ValueError with a clear, actionable message on failure."""
    username = normalize_username(username)
    if not username:
        raise ValueError("No GitHub username provided.")

    user_resp = requests.get(f"{GITHUB_API}/users/{username}", headers=_headers(), timeout=10)
    if user_resp.status_code == 404:
        raise ValueError(
            f"GitHub user '{username}' not found. Enter just your username "
            f"(e.g. 'octocat'), not the full profile URL."
        )
    if user_resp.status_code == 403:
        raise ValueError(_rate_limit_message(user_resp))
    user_resp.raise_for_status()
    profile = user_resp.json()

    repos_resp = requests.get(
        f"{GITHUB_API}/users/{username}/repos",
        params={"per_page": 100, "sort": "updated"},
        headers=_headers(),
        timeout=10,
    )
    if repos_resp.status_code == 403:
        raise ValueError(_rate_limit_message(repos_resp))
    repos_resp.raise_for_status()
    repos = repos_resp.json()

    return {"profile": profile, "repos": repos}


def extract_skills_from_github(github_data: dict) -> list[dict]:
    repos = [r for r in github_data["repos"] if not r.get("fork")]
    total_repos = len(repos) or 1

    language_counts: dict[str, int] = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            language_counts[lang] = language_counts.get(lang, 0) + 1

    results = []
    for lang, count in language_counts.items():
        canonical = ALIAS_LOOKUP.get(lang.lower())
        if not canonical:
            continue
        share = count / total_repos
        confidence = round(min(0.9, 0.4 + share * 0.6), 2)
        results.append({
            "skill_name": canonical,
            "category": SKILLS_TAXONOMY[canonical]["category"],
            "confidence": confidence,
            "evidence": f"Primary language in {count} of {total_repos} public repos",
        })

    if total_repos >= 5:
        results.append({
            "skill_name": "git",
            "category": SKILLS_TAXONOMY["git"]["category"],
            "confidence": round(min(0.9, 0.5 + total_repos * 0.02), 2),
            "evidence": f"{total_repos} public repositories",
        })

    return results
