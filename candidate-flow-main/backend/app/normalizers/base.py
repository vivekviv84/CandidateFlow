"""Base interface for normalizers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.normalizers.models import NormalizationResult


class BaseNormalizer(ABC):
    """Shared interface for normalization-only components."""

    @abstractmethod
    def normalize(self, values: list[Any], field_name: str) -> NormalizationResult:
        """Normalize extracted values without merging or conflict resolution."""

