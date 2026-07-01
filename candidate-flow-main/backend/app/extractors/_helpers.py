"""Internal helpers shared by extractor implementations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def flatten_field_values(value: Any) -> Iterable[str]:
    """Yield string leaves from nested source field values."""

    if value is None:
        return
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested_value in value.values():
            yield from flatten_field_values(nested_value)
        return
    if isinstance(value, list | tuple | set):
        for nested_value in value:
            yield from flatten_field_values(nested_value)
        return
    yield str(value)


def fragment_text_values(fields: dict[str, Any]) -> list[str]:
    """Return all string-like values from a fragment fields dictionary."""

    values: list[str] = []
    for value in fields.values():
        values.extend(flatten_field_values(value))
    return values


def unique_preserve_order(values: Iterable[Any]) -> list[Any]:
    """Deduplicate values while preserving first-seen order."""

    seen: set[str] = set()
    unique_values: list[Any] = []
    for value in values:
        marker = repr(value)
        if marker in seen:
            continue
        seen.add(marker)
        unique_values.append(value)
    return unique_values

