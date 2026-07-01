"""Path-based field mapping utilities."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


MISSING = object()


class FieldMapper:
    """Read and write nested dictionary/list values using dotted paths."""

    def get_path(self, data: Any, path: str) -> Any:
        """Return a nested value or MISSING for an unavailable path."""

        current = data
        for part in self._parts(path):
            if isinstance(current, dict):
                if part not in current:
                    return MISSING
                current = current[part]
                continue
            if isinstance(current, list):
                if not part.isdigit():
                    return MISSING
                index = int(part)
                if index >= len(current):
                    return MISSING
                current = current[index]
                continue
            return MISSING
        return deepcopy(current)

    def set_path(self, data: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested dictionary value, creating dictionaries as needed."""

        parts = self._parts(path)
        if not parts:
            return

        current = data
        for part in parts[:-1]:
            next_value = current.get(part)
            if not isinstance(next_value, dict):
                next_value = {}
                current[part] = next_value
            current = next_value
        current[parts[-1]] = deepcopy(value)

    @staticmethod
    def _parts(path: str) -> list[str]:
        return [part.strip() for part in path.split(".") if part.strip()]
