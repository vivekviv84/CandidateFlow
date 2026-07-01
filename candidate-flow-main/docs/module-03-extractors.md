# Module 03: Extractors

## Scope

This module adds six independent extractors:

- `EmailExtractor`
- `PhoneExtractor`
- `SkillsExtractor`
- `ExperienceExtractor`
- `EducationExtractor`
- `NameExtractor`

Each extractor accepts a `CandidateFragment` and returns an `ExtractionResult` containing only extracted values and extraction metadata.

## Design Notes

- Extractors do not read files. They only consume `CandidateFragment`.
- Extractors do not normalize, validate, merge, or create provenance.
- Extractors do not use LLMs. They use explicit fields, regex, and deterministic parsing.
- Confidence is extraction-level only and applies to the extractor result, not individual candidate fields.
- Unstructured parsing is intentionally conservative and expects labeled lines for skills, experience, and education.

## Edge Cases Covered

- Empty fragments return empty extraction results with `0.0` confidence.
- Email extraction preserves source casing.
- Phone extraction preserves source formatting and extensions.
- Skills extraction does not canonicalize names.
- Experience dates remain unnormalized strings.
- Education years remain source values and are not validated.
- Structured fields can be lists, dictionaries, or strings.

## Known Limitations

- Name detection from raw text uses the first short non-empty line as a fallback.
- Experience and education extraction from raw text supports simple labeled-line patterns only.
- Skill extraction is based on explicit skill fields or `Skills:` sections.
- Field-level confidence and cross-source agreement are intentionally deferred to later modules.

