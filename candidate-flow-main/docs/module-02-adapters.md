# Module 02: Source Adapters

## Scope

This module adds four source adapters:

- `CsvAdapter`
- `AtsJsonAdapter`
- `ResumeAdapter`
- `NotesAdapter`

Each adapter accepts a path for its specific source type, parses only that source, and returns `CandidateFragment` instances.

## Design Notes

- Adapters are the only modules that read CSV, JSON, PDF, or TXT files.
- Adapters preserve source values exactly enough for later normalizers to own casing, phone formats, date formats, and skill canonicalization.
- Structured sources produce fields from their source records.
- Unstructured sources produce only `raw_text`.
- Malformed readable inputs return error fragments instead of crashing.
- Missing paths and non-file paths raise because the source is unreadable.
- Confidence is only adapter-level extraction confidence.

## Edge Cases Covered

- Missing files raise `FileNotFoundError`.
- Empty CSV returns one error fragment.
- CSV rows with no values collect row-level errors.
- Malformed JSON returns one error fragment.
- JSON arrays skip non-object items and record parser errors.
- Empty notes files return a raw-text fragment with an error.
- Resume pages with no text collect page-level errors.

## Known Limitations

- `ResumeAdapter` requires `pdfplumber` at runtime for real PDF parsing.
- CSV parsing relies on `pandas.read_csv`; delimiter auto-detection is not included.
- ATS JSON schema validation is intentionally deferred to validators.
- No extraction, normalization, merging, provenance, or field-level confidence is performed in this module.

