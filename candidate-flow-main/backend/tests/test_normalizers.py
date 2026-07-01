"""Unit tests for normalization-only modules."""

from __future__ import annotations

from app.normalizers import (
    DateNormalizer,
    EmailNormalizer,
    LocationNormalizer,
    PhoneNormalizer,
    SkillsNormalizer,
)


def test_email_normalizer_trims_and_lowercases_with_steps() -> None:
    result = EmailNormalizer().normalize([" ADA@EXAMPLE.COM "])

    value = result.values[0]
    assert result.field_name == "emails"
    assert value.original_value == " ADA@EXAMPLE.COM "
    assert value.normalized_value == "ada@example.com"
    assert value.is_normalized is True
    assert value.metadata.steps == ["trimmed whitespace", "lowercased"]


def test_email_normalizer_preserves_non_string_with_warning() -> None:
    result = EmailNormalizer().normalize([123])

    value = result.values[0]
    assert value.normalized_value == 123
    assert value.is_normalized is False
    assert value.metadata.warnings == ["Email value is not a string; preserved original value."]


def test_phone_normalizer_converts_to_e164() -> None:
    result = PhoneNormalizer(default_region="US").normalize([" (415) 555-2671 "])

    value = result.values[0]
    assert value.original_value == " (415) 555-2671 "
    assert value.normalized_value == "+14155552671"
    assert value.metadata.steps == ["trimmed whitespace", "converted to E.164"]


def test_phone_normalizer_preserves_unparseable_value_with_warning() -> None:
    result = PhoneNormalizer(default_region="US").normalize(["phone unknown"])

    value = result.values[0]
    assert value.normalized_value == "phone unknown"
    assert value.is_normalized is False
    assert value.metadata.warnings[0].startswith("Phone parse failed:")


def test_date_normalizer_converts_to_year_month() -> None:
    result = DateNormalizer().normalize(["Jan 15 2024", "2024-06-30"])

    assert [value.normalized_value for value in result.values] == ["2024-01", "2024-06"]
    assert result.values[0].metadata.steps == ["converted to YYYY-MM"]


def test_date_normalizer_preserves_present_marker() -> None:
    result = DateNormalizer().normalize([" Present "])

    value = result.values[0]
    assert value.normalized_value == "Present"
    assert value.metadata.steps == ["trimmed whitespace"]
    assert value.metadata.warnings == ["Open-ended date marker preserved for later business logic."]


def test_date_normalizer_preserves_unparseable_value_with_warning() -> None:
    result = DateNormalizer().normalize(["next summer"])

    value = result.values[0]
    assert value.normalized_value == "next summer"
    assert value.is_normalized is False
    assert value.metadata.warnings[0].startswith("Date parse failed:")


def test_skills_normalizer_maps_aliases_without_deduplicating() -> None:
    result = SkillsNormalizer().normalize([" py ", "Python", "ML Ops"])

    assert [value.normalized_value for value in result.values] == ["Python", "Python", "MLOps"]
    assert result.values[0].metadata.steps == [
        "trimmed whitespace",
        "mapped alias 'py' to canonical skill 'Python'",
    ]


def test_skills_normalizer_preserves_unknown_skill_with_warning() -> None:
    result = SkillsNormalizer().normalize(["Graph Theory"])

    value = result.values[0]
    assert value.normalized_value == "Graph Theory"
    assert value.metadata.warnings == ["No canonical alias mapping found; preserved trimmed skill value."]


def test_location_normalizer_structures_city_region_country() -> None:
    result = LocationNormalizer().normalize([" Bengaluru, Karnataka, India "])

    value = result.values[0]
    assert value.normalized_value == {"city": "Bengaluru", "region": "KA", "country": "IN"}
    assert value.metadata.steps == [
        "trimmed whitespace",
        "mapped region 'Karnataka' to code 'KA'",
        "mapped country 'India' to ISO code 'IN'",
    ]


def test_location_normalizer_handles_two_part_location() -> None:
    result = LocationNormalizer().normalize(["San Francisco, USA"])

    assert result.values[0].normalized_value == {"city": "San Francisco", "region": None, "country": "US"}


def test_location_normalizer_preserves_unknown_country_with_warning() -> None:
    result = LocationNormalizer().normalize(["Paris, Wonderland"])

    value = result.values[0]
    assert value.normalized_value == {"city": "Paris", "region": None, "country": "Wonderland"}
    assert value.metadata.warnings == [
        "No country mapping found for 'Wonderland'; preserved source country."
    ]


def test_location_normalizer_structures_dict_input() -> None:
    result = LocationNormalizer().normalize([{"city": " Mumbai ", "region": "Maharashtra", "country": "IN"}])

    assert result.values[0].normalized_value == {"city": "Mumbai", "region": "MH", "country": "IN"}
    assert result.values[0].metadata.steps == [
        "trimmed city whitespace",
        "mapped region 'Maharashtra' to code 'MH'",
    ]

