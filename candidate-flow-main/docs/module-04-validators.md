# Module 04: Validators

## Scope

This module adds independent validators for:

- Email
- Phone
- Date
- URL
- Candidate schema

Each validator returns `ValidationResult` objects with:

- `is_valid`
- `severity`
- `message`
- `field`
- `suggested_action`

## Design Notes

- Validators do not normalize or modify values.
- Validators collect all issues they can find and return structured results.
- Value validators accept either one value or a list of values.
- URL validation also accepts platform-to-URL dictionaries.
- Candidate schema validation inspects candidate-like mappings directly instead of constructing a `Candidate`, because model construction may apply model-level field cleanup.

## Edge Cases Covered

- Emails with surrounding whitespace are flagged but left unchanged.
- Invalid email formats are reported per item.
- Phone values with too few or too many digits are rejected.
- Phone values with unexpected characters are warnings.
- Date validation accepts common source date formats and open-ended markers such as `Present`.
- URL validation requires `http` or `https` and a domain host.
- Candidate schema validation collects missing required fields, wrong field types, invalid collection item types, bad link value types, and out-of-range confidence.

## Known Limitations

- Phone validation is plausibility-based and does not use country-specific rules.
- Date validation supports a conservative set of deterministic formats only.
- URL validation does not check whether a URL is reachable.
- Candidate schema validation checks shape, not semantic correctness of every nested object.

