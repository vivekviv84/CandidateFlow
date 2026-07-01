"""Duplicate grouping helpers for merge resolvers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.merger.models import MergeCandidateValue


class DuplicateDetector:
    """Group duplicate values without selecting winners."""

    def group_exact(self, values: list[MergeCandidateValue]) -> list[list[MergeCandidateValue]]:
        """Group exact duplicate values."""

        groups: dict[str, list[MergeCandidateValue]] = defaultdict(list)
        for value in values:
            groups[self._key(value.value)].append(value)
        return list(groups.values())

    def group_skills(self, values: list[MergeCandidateValue]) -> list[list[MergeCandidateValue]]:
        """Group skills by canonical name when available, otherwise name."""

        groups: dict[str, list[MergeCandidateValue]] = defaultdict(list)
        for value in values:
            skill = value.value
            key = skill.get("canonical_name") or skill.get("name") if isinstance(skill, dict) else skill
            groups[str(key)].append(value)
        return list(groups.values())

    def group_links(self, values: list[MergeCandidateValue]) -> dict[str, list[MergeCandidateValue]]:
        """Group link values by platform."""

        groups: dict[str, list[MergeCandidateValue]] = defaultdict(list)
        for value in values:
            if isinstance(value.value, dict):
                platform = str(value.value.get("platform"))
                groups[platform].append(value)
        return groups

    def group_experience(self, values: list[MergeCandidateValue]) -> list[list[MergeCandidateValue]]:
        """Group experience entries by company and title identity."""

        groups: dict[str, list[MergeCandidateValue]] = defaultdict(list)
        for value in values:
            item = value.value
            company = self._dict_text(item, "company")
            title = self._dict_text(item, "title")
            groups[f"{company}|{title}"].append(value)
        return list(groups.values())

    def group_education(self, values: list[MergeCandidateValue]) -> list[list[MergeCandidateValue]]:
        """Group education entries by institution, degree, field, and end year."""

        groups: dict[str, list[MergeCandidateValue]] = defaultdict(list)
        for value in values:
            item = value.value
            key = "|".join(
                [
                    self._dict_text(item, "institution"),
                    self._dict_text(item, "degree"),
                    self._dict_text(item, "field"),
                    self._dict_text(item, "end_year"),
                ]
            )
            groups[key].append(value)
        return list(groups.values())

    @staticmethod
    def _dict_text(value: Any, key: str) -> str:
        if not isinstance(value, dict):
            return ""
        item = value.get(key)
        return "" if item is None else str(item)

    @staticmethod
    def _key(value: Any) -> str:
        if isinstance(value, dict):
            return repr(sorted((str(key), DuplicateDetector._key(item)) for key, item in value.items()))
        if isinstance(value, list):
            return repr([DuplicateDetector._key(item) for item in value])
        return repr(value)

