"""GitHub public profile adapter.

Fetches a candidate's public GitHub profile and repository languages,
converting them into a CandidateFragment consistent with all other adapters.

Design decisions:
- Uses GitHub's unauthenticated REST API. Rate limit is 60 req/hr per IP.
  In production this would use a personal access token via Authorization header.
  For this take-home, unauthenticated is sufficient for correctness demonstration.
- Repository languages are treated as a WEAK skill signal (lower confidence
  than an explicit listing): knowing someone used Python in a repo doesn't
  imply proficiency. This is recorded in the fragment's confidence field and
  flows through to per-skill confidence scoring in the confidence engine.
- Network failure, 404, or rate limit -> logs warning and returns an empty
  list. The pipeline degrades gracefully -- other sources continue unaffected.
- We cap repos at 100 (one page, sorted by recently updated) -- enough
  signal without over-engineering pagination for this scope.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.models import CandidateFragment
from app.models.candidate_fragment import SourceType

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
TIMEOUT_SECONDS = 8
REPO_PAGE_SIZE = 100

# Repo languages -> our canonical skill names where they differ
LANGUAGE_SKILL_MAP: dict[str, str] = {
    "Jupyter Notebook": "Python",
    "Shell": "Bash",
    "Makefile": "Make",
}


def _canonical_language(lang: str) -> str:
    return LANGUAGE_SKILL_MAP.get(lang, lang)


class GitHubAdapter:
    """Fetch and convert a GitHub public profile into a CandidateFragment."""

    def load(self, username: str) -> list[CandidateFragment]:
        """
        Fetch a GitHub user's public profile and infer skills from repo languages.

        Returns [] on any failure (404, rate limit, network error). The caller
        pipeline continues with whatever other sources are available.
        """
        username = (username or "").strip().lstrip("@")
        if not username:
            logger.warning("GitHubAdapter.load called with empty username. Skipping.")
            return []

        profile_data = self._fetch_profile(username)
        if profile_data is None:
            return []

        skill_names = self._fetch_repo_languages(username)

        fields: dict[str, Any] = {}

        if profile_data.get("name"):
            fields["full_name"] = profile_data["name"]

        if profile_data.get("email"):
            fields["emails"] = [profile_data["email"]]

        if profile_data.get("bio"):
            fields["headline"] = profile_data["bio"]

        if profile_data.get("location"):
            fields["location"] = profile_data["location"]

        if profile_data.get("html_url"):
            fields["links"] = {"github": profile_data["html_url"]}

        if profile_data.get("blog"):
            links = fields.setdefault("links", {})
            links["portfolio"] = profile_data["blog"]

        if skill_names:
            # Repo languages are a weak signal -- wrap as skill dicts with
            # low base confidence so the confidence engine can score them
            # correctly relative to explicitly-listed skills.
            fields["skills"] = [
                {"name": name, "canonical_name": name, "confidence": 0.6}
                for name in skill_names
            ]

        fragment = CandidateFragment(
            source=SourceType.GITHUB,
            # Lower base confidence than structured sources -- self-reported,
            # no recruiter verification step.
            confidence=0.65,
            fields=fields,
            metadata={
                "github_username": username,
                "public_repos": profile_data.get("public_repos", 0),
                "followers": profile_data.get("followers", 0),
            },
        )

        logger.info(
            "GitHubAdapter: loaded profile for '%s' — %d field(s), %d skill(s)",
            username,
            len(fields),
            len(skill_names),
        )
        return [fragment]

    def _fetch_profile(self, username: str) -> dict[str, Any] | None:
        """Return the raw GitHub user API response, or None on any failure."""
        url = f"{GITHUB_API_BASE}/users/{username}"
        try:
            resp = requests.get(url, timeout=TIMEOUT_SECONDS, headers={"Accept": "application/vnd.github+json"})
        except requests.RequestException as exc:
            logger.warning("GitHubAdapter: network error fetching '%s': %s. Skipping.", username, exc)
            return None

        if resp.status_code == 404:
            logger.warning("GitHubAdapter: user '%s' not found (404). Skipping.", username)
            return None
        if resp.status_code == 403:
            logger.warning("GitHubAdapter: rate limit hit for '%s' (403). Skipping.", username)
            return None
        if resp.status_code != 200:
            logger.warning("GitHubAdapter: unexpected status %d for '%s'. Skipping.", resp.status_code, username)
            return None

        return resp.json()

    def _fetch_repo_languages(self, username: str) -> list[str]:
        """Return canonical language names from the user's public repos."""
        url = f"{GITHUB_API_BASE}/users/{username}/repos"
        try:
            resp = requests.get(
                url,
                timeout=TIMEOUT_SECONDS,
                params={"per_page": REPO_PAGE_SIZE, "sort": "updated"},
                headers={"Accept": "application/vnd.github+json"},
            )
        except requests.RequestException as exc:
            logger.warning("GitHubAdapter: could not fetch repos for '%s': %s. Continuing without repo skills.", username, exc)
            return []

        if resp.status_code != 200:
            logger.warning("GitHubAdapter: repos returned status %d for '%s'. Continuing without repo skills.", resp.status_code, username)
            return []

        repos = resp.json()
        seen: set[str] = set()
        result: list[str] = []
        for repo in repos:
            lang = repo.get("language")
            if lang and lang not in seen:
                seen.add(lang)
                result.append(_canonical_language(lang))
        return result
