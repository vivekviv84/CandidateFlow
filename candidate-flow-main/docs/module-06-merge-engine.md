# Module 06: Merge Engine

## Scope

This module adds the deterministic merge engine.

Input:

- `list[CandidateFragment]`

Output:

- `Candidate`
- `MergeReport`

## Responsibilities

- Resolve conflicts deterministically.
- Merge duplicate values.
- Generate merge decisions.
- Generate candidate provenance from merge decisions.
- Produce one canonical candidate.

## Boundaries

The merge engine does not:

- Read files
- Validate values
- Normalize values
- Use regex
- Parse documents
- Calculate source extraction results

## Strategy

Scalar values are resolved by:

1. Highest confidence
2. Highest source priority
3. Newest extraction timestamp
4. Stable deterministic value ordering

List values are unioned and deduplicated by exact value.

Links keep one URL per platform.

Skills are deduplicated by `canonical_name` when available, otherwise `name`.

Experience entries are grouped by exact company and title, then dates and summaries are merged inside the group.

Education entries are grouped by exact institution, degree, field, and end year.

## Known Limitations

- Experience and education duplicate detection is exact-match based.
- Fuzzy matching is intentionally deferred.
- Candidate model construction may still apply model-level cleanup from Module 01.
- `overall_confidence` is a simple average of merge decision confidence until the dedicated confidence engine is implemented.

