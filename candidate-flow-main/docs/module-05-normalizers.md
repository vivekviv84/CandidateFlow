# Module 05: Normalizers

## Scope

This module adds independent normalizers for:

- Email
- Phone
- Date
- Skills
- Location

Each normalizer accepts extracted values and returns `NormalizationResult` values with source-preserving metadata.

## Design Notes

- Normalizers do not merge, deduplicate, validate, or resolve conflicts.
- Every input value produces one output record.
- Failed normalization preserves the original value and records a warning.
- Metadata records each transformation step so the provenance engine can explain later decisions.
- Phone normalization uses `phonenumbers` and emits E.164 when parsing succeeds.
- Date normalization emits `YYYY-MM` when parsing succeeds.
- Skill normalization uses a deterministic alias map.
- Location normalization structures simple strings into city, region, and country where possible.

## Edge Cases Covered

- Non-string email, phone, date, and skill values are preserved with warnings.
- Unparseable phones and dates are preserved with warnings.
- Open-ended date markers such as `Present` are preserved.
- Unknown skills are preserved with warnings.
- Unknown countries are preserved with warnings.
- Location dictionaries and comma-separated strings are both supported.
- Duplicate normalized skills are not deduplicated because merging belongs to a later module.

## Known Limitations

- Phone normalization defaults to the `US` region unless a different region is injected.
- Date parsing relies on deterministic `dateutil` parsing and does not handle ranges.
- Skill aliases are a small configurable dictionary, not a taxonomy service.
- Location normalization does not geocode or verify that city, region, and country combinations are real.

