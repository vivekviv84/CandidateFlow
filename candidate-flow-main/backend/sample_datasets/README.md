# Sample Datasets

These fixtures are intended for dashboard demos, manual API checks, and end-to-end integration tests.

- `valid`: clean multi-source candidate with CSV, ATS JSON, notes, and projection config.
- `conflicts`: intentionally conflicting names and emails across CSV, ATS JSON, and notes.
- `duplicates`: repeated values across sources to exercise merge-report discarded values.
- `missing_fields`: sparse sources where missing scalar fields should not block projection.
- `invalid_inputs`: malformed JSON plus weak CSV/notes data for graceful-failure checks.

Example:

```powershell
python main.py transform --csv sample_datasets/valid/recruiter.csv --ats sample_datasets/valid/ats.json --notes sample_datasets/valid/notes.txt --config sample_datasets/valid/config.json
```
