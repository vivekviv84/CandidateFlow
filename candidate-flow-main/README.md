# Candidate Flow

**Explainable multi-source candidate data transformation engine.**  
Eightfold Engineering Intern Assignment — Vivek Kumar Dubey · vivekviv84@gmail.com

---

## What it does

Ingests candidate data from multiple heterogeneous sources, merges them into a single canonical profile, and emits schema-valid JSON with full field-level provenance and confidence scoring. Every field in the output can answer: *where did I come from, why was I selected, and how confident are we?*

**Pipeline:**
```
Ingest → Extract → Normalize → Merge → Score → Project → Validate
```

**Sources supported:**
| Source | Type | Notes |
|--------|------|-------|
| Recruiter CSV | Structured | Column-alias mapping for varying headers |
| ATS JSON blob | Structured | Field names do NOT match our schema — mapped via extractors |
| Resume PDF | Unstructured | Text extraction via pdfplumber |
| Recruiter notes TXT | Unstructured | Regex-based email/phone/skill extraction |
| GitHub profile URL | Unstructured | Public REST API — name, bio, repo languages as skill signal |

---

## Quickstart

### 1. Install backend dependencies

```bash
cd backend
pip install -e ".[dev]"
```

Or without editable install:
```bash
pip install fastapi uvicorn pydantic phonenumbers python-dateutil pycountry \
            pdfplumber requests typer pytest httpx python-multipart
```

### 2. Run the API server

```bash
cd backend
uvicorn app.api.main:app --reload
```

Open **http://localhost:8000/docs** — interactive Swagger UI where you can upload files and run the pipeline.

### 3. Run via CLI

```bash
cd backend

# Full transform — all sources
python main.py transform \
  --csv sample_datasets/valid/recruiter.csv \
  --ats sample_datasets/valid/ats.json \
  --notes sample_datasets/valid/notes.txt \
  --config sample_datasets/valid/config.json

# Explain a field decision (why was full_name chosen from this source?)
python main.py explain --field full_name \
  --csv sample_datasets/conflicts/recruiter.csv \
  --ats sample_datasets/conflicts/ats.json \
  --notes sample_datasets/conflicts/notes.txt
```

### 4. Run the React UI

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — drag-and-drop files, see confidence scores, merge decisions, provenance trail, and pipeline timeline.

### 5. Run tests

```bash
cd backend
python -m pytest -v
```

---

## Sample datasets

All sample inputs are in `backend/sample_datasets/`:

| Folder | What it demonstrates |
|--------|----------------------|
| `valid/` | Clean happy-path — CSV + ATS JSON + notes all consistent |
| `conflicts/` | Conflicting values across sources — tests merge resolution |
| `duplicates/` | Same candidate appearing in CSV + ATS — tests dedup logic |
| `missing_fields/` | Incomplete sources — tests graceful degradation |
| `invalid_inputs/` | Garbage values — malformed phone, bad email, corrupt data |

Run the conflict dataset and then call `/explain` to see the merge decision explained end-to-end.

---

## Architecture

```
backend/app/
  adapters/         Source adapters — each adapter returns a CandidateFragment
    csv_adapter.py
    ats_json_adapter.py
    resume_adapter.py
    notes_adapter.py
  extractors/       Field extractors — pull typed values from raw adapter output
    email.py / phone.py / name.py / skills.py / experience.py / education.py
  normalizers/      Pure normalization functions (phone→E.164, date→YYYY-MM, etc.)
  merger/           Deterministic merge engine with per-field resolver strategy
    merge_engine.py
    duplicate_detector.py
    field_resolvers/  One resolver per field type (scalar, list, skill, experience…)
    source_priority.py
  confidence/       Weighted confidence scoring per field and overall
  projection/       Runtime config-driven output reshaping (no code changes)
  provenance/       Builds full provenance trail — field, source, method, reason
  validators/       Output validation — email, phone, date, URL, schema
  api/              FastAPI app — /transform, /explain, /health endpoints
frontend/           React + Vite + Tailwind — file upload UI with tabbed output
```

**Key design principle:** The canonical record is always built in full. The projection layer only reads from it — it never re-derives data. This means there is exactly one normalization pipeline and the system is fully deterministic.

---

## Runtime config (projection layer)

Pass a `config.json` to reshape output without any code changes:

```json
{
  "fields": [
    {"path": "full_name", "type": "string", "required": true},
    {"path": "primary_email", "from": "emails[0]", "type": "string", "required": true},
    {"path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164"},
    {"path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical"}
  ],
  "include_confidence": true,
  "include_provenance": false,
  "on_missing": "null"
}
```

`on_missing` accepts `null` (default), `omit`, or `error`.

---

## Merge / conflict resolution

**Source priority (highest trust first):** ATS JSON → Recruiter CSV → Resume PDF → Recruiter notes

Scalar fields (name, headline): highest-priority non-null source wins. Every rejected value is still recorded in provenance as `conflict_discarded` — nothing is silently lost.

Array fields (emails, phones, skills): union with dedup. Phones are deduped *after* E.164 normalization so two raw strings resolving to the same number collapse to one entry.

Call `/explain` with a field name after any `/transform` to get the full decision chain: selected value, rejected values, source, rule, and confidence.

---

## Confidence scoring

- **Per-skill:** 0.95 if confirmed by ≥2 independent sources, lower for single-source
- **Per-field:** 1.0 for uncontested structured source, 0.75 for conflict-resolved, 0.6 unstructured-only, 0.2 parse-failed, 0.0 missing
- **Overall:** Weighted mean across fields by hiring relevance (name/email weighted highest)

---

## Deliberately descoped

- **LinkedIn scraping** — ToS risk + auth complexity; fragile in production
- **Async concurrent fetching** — not needed at this scale; noted as clear next step for thousands of candidates
- **OCR for scanned PDFs** — pdfplumber handles text-layer PDFs; OCR adds tesseract dependency without meaningful signal gain for a take-home

---

## Demo video script (≈2 min)

1. Start API + React UI, show the upload interface
2. Upload `sample_datasets/valid/` files → show clean merged output with confidence scores
3. Upload `sample_datasets/conflicts/` files → show conflict resolution in Merge Report tab
4. Call `/explain` on `full_name` → explain why one source won over another
5. Show `sample_datasets/invalid_inputs/` — garbage phone, bad email → pipeline completes, no crash, unknown values null
