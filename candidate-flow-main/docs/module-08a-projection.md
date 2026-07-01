# Module 8A: Projection Layer

## Scope

This module adds the projection layer:

- `Projector`
- `ProjectionConfig`
- `FieldMapper`
- `MissingFieldStrategy`

## Responsibilities

- Project a canonical `Candidate` into JSON-compatible output.
- Select output fields.
- Rename fields.
- Map nested paths from source to output.
- Include or exclude confidence fields.
- Include or exclude provenance.
- Handle missing paths with `null`, `omit`, or `error`.

## Boundaries

The projection layer does not read files, call FastAPI, render React, validate, normalize, merge, or compute confidence.

## Path Semantics

- Paths use dot notation.
- Dictionary keys are addressed by name.
- List indexes are addressed with numeric path parts, such as `emails.0`.
- `field_mappings` are interpreted as `output_path -> source_path`.
- `rename_fields` are interpreted as `source_path -> output_path` for selected fields.

## Known Limitations

- `FieldMapper.set_path` creates dictionaries only; it does not create list structures in output paths.
- If both `field_mappings` and `selected_fields` are provided, explicit mappings take precedence.
