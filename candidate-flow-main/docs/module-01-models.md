# Module 01: Shared Candidate Models

## Scope

This module defines the shared Pydantic contracts used by the rest of the pipeline:

- `CandidateFragment`
- `Candidate`
- `Skill`
- `Experience`
- `Education`
- `ProvenanceRecord`
- `RuntimeConfig`

## Design Notes

- Source adapters must emit `CandidateFragment`; downstream modules should not read CSV, JSON, PDF, or TXT directly.
- Models use `extra="forbid"` so unknown fields fail fast in tests and config loading.
- Confidence values are bounded between `0.0` and `1.0`.
- Candidate email and phone lists are deduplicated deterministically while preserving first-seen order.
- Source priority defaults encode the required merge priority: ATS JSON, Recruiter CSV, Resume, Recruiter Notes.

## Edge Cases Covered

- Blank parser errors are removed.
- Duplicate emails and phones are deduplicated.
- Email casing and whitespace are normalized.
- Invalid confidence scores are rejected.
- Unknown config keys are rejected.
- Blank configured output fields are rejected.

## Known Limitations

- Phone strings are not converted to E.164 in this module; that belongs in the phone normalizer.
- Skill canonicalization is not performed here; this module only trims skill strings.
- Date validation for `Experience.start_date` and `Experience.end_date` is deferred to the date normalizer and validator.
- `extracted_at` defaults to current UTC time when adapters omit it, so adapters should pass a fixed timestamp in deterministic fixture tests.

