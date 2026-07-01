# Candidate Flow

**Explainable Multi-Source Candidate Data Transformation Engine**

Candidate Flow is an end-to-end data transformation pipeline that ingests candidate information from multiple heterogeneous sources, normalizes inconsistent data, resolves conflicts deterministically, and produces a single canonical candidate profile with complete provenance and confidence scoring.

Built as part of the **Eightfold AI Engineering Internship Assignment (Jul–Dec 2026)**.

---

# Features

- Multi-source candidate ingestion
- Structured and unstructured source support
- Canonical profile generation
- Deterministic conflict resolution
- Field-level confidence scoring
- Full provenance tracking
- Runtime configurable output projection
- REST API (FastAPI)
- Interactive React UI
- Command Line Interface (CLI)
- Comprehensive unit and integration tests

---

# Supported Input Sources

| Source | Type |
|----------|------|
| Recruiter CSV | Structured |
| ATS JSON | Structured |
| Resume PDF | Unstructured |
| Recruiter Notes (.txt) | Unstructured |
| Runtime Config | JSON |

---

# Processing Pipeline

```
Ingest
    ↓
Extract
    ↓
Normalize
    ↓
Merge
    ↓
Conflict Resolution
    ↓
Confidence Scoring
    ↓
Projection
    ↓
Validation
    ↓
Canonical Candidate JSON
```

---

# Repository Structure

```
candidate-flow-main/
│
├── backend/
│   ├── app/
│   ├── tests/
│   ├── sample_datasets/
│   ├── main.py
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
│
├── docs/
│
└── README.md
```

---

# Technology Stack

## Backend

- Python 3.12+
- FastAPI
- Typer CLI
- Pydantic
- Pandas
- pdfplumber
- Requests
- Pytest

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS

---

# Requirements

## Backend

- Python 3.12+
- pip

## Frontend

- Node.js 20+
- npm

---

# Installation

Clone the repository.

```bash
git clone https://github.com/vivekviv84/CandidateFlow.git

cd CandidateFlow/candidate-flow-main
```

---

# Backend Setup

Navigate into the backend.

```bash
cd backend
```

Create a virtual environment.

### Windows

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv

source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

---

# Run Backend API

```bash
uvicorn app.api.main:app --reload --port 8010
```

API Documentation

```
http://127.0.0.1:8010/docs
```

Health Check

```
http://127.0.0.1:8010/health
```

---

# Frontend Setup

Open another terminal.

```bash
cd candidate-flow-main/frontend
```

Install packages.

```bash
npm install
```

---

## Configure API Target

Create a file named

```
.env.local
```

inside the frontend folder.

Contents:

```text
VITE_API_TARGET=http://127.0.0.1:8010
```

---

Run the frontend.

```bash
npm run dev
```

Open

```
http://localhost:5173
```

---

# Running the CLI

Navigate to backend.

```bash
cd backend
```

Show available commands.

```bash
python main.py --help
```

Print application version.

```bash
python main.py version
```

Health check.

```bash
python main.py health
```

---

# Transform Example

```bash
python main.py transform ^
--csv sample_datasets/valid/recruiter.csv ^
--ats sample_datasets/valid/ats.json ^
--notes sample_datasets/valid/notes.txt ^
--config sample_datasets/valid/config.json
```

### Linux/macOS

```bash
python main.py transform \
--csv sample_datasets/valid/recruiter.csv \
--ats sample_datasets/valid/ats.json \
--notes sample_datasets/valid/notes.txt \
--config sample_datasets/valid/config.json
```

---

# Explain Merge Decision

```bash
python main.py explain ^
--field full_name ^
--csv sample_datasets/conflicts/recruiter.csv ^
--ats sample_datasets/conflicts/ats.json ^
--notes sample_datasets/conflicts/notes.txt
```

---

# Running Tests

From backend:

```bash
python -m pytest -v
```

---

# Sample Datasets

Located in

```
backend/sample_datasets/
```

| Folder | Purpose |
|----------|---------|
| valid | Happy path |
| conflicts | Merge conflicts |
| duplicates | Duplicate candidates |
| missing_fields | Missing information |
| invalid_inputs | Invalid values |

---

# API Endpoints

| Endpoint | Description |
|------------|------------|
| POST /transform | Transform candidate data |
| POST /explain | Explain merge decisions |
| GET /health | Health check |
| GET /version | Application version |
| GET /docs | Swagger UI |
| GET /openapi.json | OpenAPI specification |

---

# Merge Strategy

Scalar fields:

- Highest confidence
- Source priority
- Timestamp
- Stable deterministic ordering

Collection fields:

- Union
- Deduplicate
- Normalize
- Preserve provenance

---

# Provenance

Every selected value records

- Source
- Merge strategy
- Confidence
- Timestamp
- Discarded alternatives
- Processing stage

---

# Confidence Scoring

Confidence is computed using multiple factors including

- Source reliability
- Data completeness
- Cross-source agreement
- Normalization success
- Conflict resolution

Overall confidence is calculated independently from field-level confidence.

---

# Output

Produces a canonical JSON profile containing

- Candidate information
- Confidence
- Merge report
- Provenance
- Processing summary

---

# Design Principles

- Deterministic
- Explainable
- Configurable
- Robust
- Extensible
- Production-oriented

---

# Future Improvements

- LinkedIn adapter
- OCR support for scanned resumes
- Async processing
- Parallel ingestion
- Redis caching
- PostgreSQL persistence
- Authentication
- Docker deployment
- Kubernetes support

---

# Author

**Vivek Kumar Dubey**

Eightfold AI Engineering Internship Assignment

GitHub

https://github.com/vivekviv84/CandidateFlow

Email

vivekviv84@gmail.com

---
