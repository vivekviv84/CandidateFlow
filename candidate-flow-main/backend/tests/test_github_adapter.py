"""Tests for the GitHub adapter.

All tests mock the HTTP layer so no network calls are made.
This keeps tests deterministic, fast, and runnable offline.
"""
from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.github_adapter import GitHubAdapter
from app.models.candidate_fragment import SourceType


@pytest.fixture
def adapter() -> GitHubAdapter:
    return GitHubAdapter()


def _mock_response(status_code: int, json_data: dict | list | None = None) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    return mock


class TestGitHubAdapterHappyPath:
    def test_returns_fragment_with_correct_source_type(self, adapter):
        profile = {"name": "Vivek Dubey", "bio": "Data Science student", "html_url": "https://github.com/vivekviv84",
                   "location": "Bengaluru", "email": None, "blog": None, "public_repos": 10, "followers": 5}
        repos = [{"language": "Python"}, {"language": "TypeScript"}, {"language": None}]

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(200, profile), _mock_response(200, repos)]
            records = adapter.load("vivekviv84")

        assert len(records) == 1
        assert records[0].source == SourceType.GITHUB

    def test_extracts_name_headline_and_location(self, adapter):
        profile = {"name": "Vivek Dubey", "bio": "ML engineer", "html_url": "https://github.com/vivekviv84",
                   "location": "Bengaluru", "email": None, "blog": None, "public_repos": 5, "followers": 2}

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(200, profile), _mock_response(200, [])]
            records = adapter.load("vivekviv84")

        f = records[0].fields
        assert f["full_name"] == "Vivek Dubey"
        assert f["headline"] == "ML engineer"
        assert f["location"] == "Bengaluru"

    def test_repo_languages_become_skills(self, adapter):
        profile = {"name": "Dev", "bio": None, "html_url": "https://github.com/dev",
                   "location": None, "email": None, "blog": None, "public_repos": 3, "followers": 0}
        repos = [{"language": "Python"}, {"language": "TypeScript"}, {"language": "Python"}]  # Python deduped

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(200, profile), _mock_response(200, repos)]
            records = adapter.load("dev")

        skill_names = [s["name"] for s in records[0].fields["skills"]]
        assert "Python" in skill_names
        assert "TypeScript" in skill_names
        assert skill_names.count("Python") == 1  # deduplicated

    def test_confidence_is_lower_than_structured_sources(self, adapter):
        profile = {"name": "Dev", "bio": None, "html_url": "https://github.com/dev",
                   "location": None, "email": None, "blog": None, "public_repos": 0, "followers": 0}

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(200, profile), _mock_response(200, [])]
            records = adapter.load("dev")

        # GitHub is self-reported and unverified -- should score below structured sources (0.8+)
        assert records[0].confidence < 0.8


class TestGitHubAdapterEdgeCases:
    def test_empty_username_returns_empty_list_no_crash(self, adapter):
        records = adapter.load("")
        assert records == []

    def test_none_username_returns_empty_list_no_crash(self, adapter):
        records = adapter.load(None)
        assert records == []

    def test_404_returns_empty_list_no_crash(self, adapter):
        with patch("requests.get", return_value=_mock_response(404)):
            records = adapter.load("nonexistent-user-xyz")
        assert records == []

    def test_403_rate_limit_returns_empty_list_no_crash(self, adapter):
        with patch("requests.get", return_value=_mock_response(403)):
            records = adapter.load("rate-limited-user")
        assert records == []

    def test_network_error_returns_empty_list_no_crash(self, adapter):
        import requests as req
        with patch("requests.get", side_effect=req.RequestException("timeout")):
            records = adapter.load("any-user")
        assert records == []

    def test_repo_api_failure_still_returns_profile_fragment(self, adapter):
        """If repos call fails, we still get a fragment from the profile -- partial > nothing."""
        profile = {"name": "Dev", "bio": "engineer", "html_url": "https://github.com/dev",
                   "location": None, "email": None, "blog": None, "public_repos": 5, "followers": 0}

        import requests as req
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _mock_response(200, profile),
                req.RequestException("repos timeout"),
            ]
            records = adapter.load("dev")

        # Profile fragment should exist even without skill signal from repos
        assert len(records) == 1
        assert records[0].fields["full_name"] == "Dev"
        assert "skills" not in records[0].fields

    def test_at_sign_prefix_stripped_from_username(self, adapter):
        """@vivekviv84 and vivekviv84 should call the same API endpoint."""
        profile = {"name": "Dev", "bio": None, "html_url": "https://github.com/dev",
                   "location": None, "email": None, "blog": None, "public_repos": 0, "followers": 0}

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(200, profile), _mock_response(200, [])]
            records = adapter.load("@dev")

        assert len(records) == 1
