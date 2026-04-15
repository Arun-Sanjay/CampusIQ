"""GitHub import for the Resume Builder (Phase 14, F6).

Pulls a user's public repos via GitHub's REST API. Unauthenticated requests
are rate-limited to 60/hr per IP — plenty for a course project. We sort by
stars and return the top N as project entries ready to merge into the resume.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
TIMEOUT_SECONDS = 8


@dataclass
class GitHubRepo:
    name: str
    description: str
    tech: list[str]
    url: str
    stars: int


def fetch_top_repos(username: str, *, top_n: int = 5) -> list[GitHubRepo]:
    """Fetch the user's most-starred public repos. Skips forks and archived ones."""
    if not username.strip():
        raise HTTPException(status_code=400, detail="GitHub username is required")

    try:
        resp = requests.get(
            f"{GITHUB_API}/users/{username}/repos",
            params={"per_page": 100, "type": "owner", "sort": "updated"},
            headers={"Accept": "application/vnd.github+json"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        logger.warning("GitHub fetch failed for %s: %s", username, e)
        raise HTTPException(
            status_code=502, detail=f"Could not reach GitHub: {e}"
        ) from e

    if resp.status_code == 404:
        raise HTTPException(
            status_code=404, detail=f"GitHub user '{username}' not found"
        )
    if resp.status_code == 403:
        raise HTTPException(
            status_code=429,
            detail="GitHub rate limit reached. Try again in an hour.",
        )
    if not resp.ok:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub returned {resp.status_code}: {resp.text[:200]}",
        )

    repos: list[dict] = resp.json() or []
    if not isinstance(repos, list):
        raise HTTPException(status_code=502, detail="Unexpected GitHub response")

    # Filter out forks + archived, sort by stars desc, take top N
    candidates = [
        r
        for r in repos
        if not r.get("fork") and not r.get("archived")
    ]
    candidates.sort(key=lambda r: int(r.get("stargazers_count") or 0), reverse=True)

    out: list[GitHubRepo] = []
    for r in candidates[:top_n]:
        topics = r.get("topics") or []
        language = r.get("language")
        tech: list[str] = []
        if language:
            tech.append(language)
        # Add up to 4 distinct topics
        for t in topics:
            if t and t not in tech:
                tech.append(t)
            if len(tech) >= 6:
                break

        out.append(
            GitHubRepo(
                name=str(r.get("name") or "").strip() or "Untitled Repo",
                description=str(r.get("description") or "").strip(),
                tech=tech,
                url=str(r.get("html_url") or ""),
                stars=int(r.get("stargazers_count") or 0),
            )
        )

    return out
