# CLAUDE.md — Diez Data Classification Tool (KSA)

## What this project is

A data discovery and governance demo tool for KSA (Saudi Arabia) clients. It scans uploaded files, detects sensitive data using regex patterns and keyword dictionaries, classifies documents by type, maps findings to KSA regulatory frameworks (NDMO and KSA PDPL), and presents results in an interactive dashboard.

## Running the app

```bash
# Run both frontend and backend together
python run.py

# Or separately:
# Backend (port 8000)
cd backend && uvicorn main:app --port 8000 --reload

# Frontend (port 5173)
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173**. API docs at **http://localhost:8000/docs**.

## Environment setup

Copy `.env.example` to `backend/.env` and add at least one LLM key:

```
ANTHROPIC_API_KEY=...   # preferred
OPENAI_API_KEY=...      # fallback
```

If neither key is set, LLM classification is skipped and the rule-based engine output is used as-is.

## Architecture

```
frontend/               React + Vite, port 5173
├── src/App.jsx         Shell: tabs, global state (scannedDocs, fw, frameworks)
├── src/config.js       API base URL and color constants
├── src/components.jsx  Shared UI: Pill, SevBadge, SrcIcon, Card, etc.
└── src/tabs/
    ├── Upload.jsx      Drag-drop file upload, per-file progress
    ├── Datasets.jsx    Structured data explorer (dynamic + static)
    ├── DocScan.jsx     Scan results table (sort, filter)
    ├── DocDetail.jsx   Signal analysis + column-level metadata
    └── ExecSummary.jsx Charts, recommendations, XLSX export

backend/                FastAPI, port 8000
├── main.py             Routes: /api/scan, /api/scan-batch, /api/frameworks, /api/export, /api/results
├── pipeline.py         Orchestrator — chains all steps, returns result dict
├── extractors.py       File extractors: xlsx, csv, txt, docx, pdf → {text, structured, cols, rows}
├── detectors.py        20+ regex patterns, 18 keyword dicts, column matchers
├── engine.py           Doc-type classifier, 9 signal rules, confidence scorer, redactor
├── frameworks.py       NDMO + KSA PDPL tier definitions and mapping logic
├── llm.py              LLM classification via OpenAI or Anthropic
└── export.py           XLSX report generation with openpyxl
```

## Detection pipeline (per file)

```
Upload → extractors.py  (by file extension)
       → detectors.py   pattern detection (regex) OR column detection (structured files)
       → detectors.py   keyword detection (18 dictionaries)
       → engine.py      doc-type classification (filename + content heuristics)
       → engine.py      9-signal analysis with co-occurrence + severity escalation
       → engine.py      confidence score + risk score (0-100)
       → frameworks.py  NDMO / KSA PDPL tier assignment
       → llm.py         LLM override of file-tier + column-tiers + assessment
       → pipeline.py    result dict assembled and returned to main.py
```

### Critical pipeline rule

For structured files (xlsx/csv), **only column-name matching runs** — do NOT run text-based regex on `pandas .to_string()` output. Number sequences in IBANs/dates/IDs create false positives when parsed as free text (see comment in `pipeline.py:35`).

## Frameworks

Two frameworks are supported, selectable in the UI:

| Key | Full name | Tiers |
|-----|-----------|-------|
| `ndmo` | Saudi National Data Management Office | Public → Confidential → Secret → Top Secret |
| `pdpl` | KSA Personal Data Protection Law | Non-personal → Personal → Sensitive personal → Sensitive restricted |

Tier keys throughout the codebase are `"open"`, `"conf"`, `"sens"`, `"secret"`.

## LLM classification (`backend/llm.py`)

- Sends **only metadata** (signal names, column names, detector results, row counts) to the LLM — never actual data values.
- LLM result overrides the rule-based tier and column-level tiers.
- Hard floors and caps are enforced in `pipeline.py` after the LLM responds:
  - National ID / Iqama / passport / biometric → floor at `"sens"`, LLM cannot downgrade.
  - Name / email / phone / salary / IBAN etc. → cap at `"conf"`, LLM cannot escalate.
  - Employee ID / department / job title etc. → cap at `"open"`.
- Uses `claude-sonnet-4-20250514` (Anthropic) or `gpt-4o` (OpenAI), 800 max tokens, temperature 0.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/frameworks` | Framework definitions (frontend bootstraps from here) |
| POST | `/api/scan` | Scan single file (multipart) |
| POST | `/api/scan-batch` | Scan multiple files |
| GET | `/api/export?framework=ndmo` | Download XLSX report |
| DELETE | `/api/results` | Clear in-memory scan store |

Scan results are stored **in memory only** — they reset when the backend restarts.

## Key design decisions

- **No database.** `scan_store` in `main.py` is a plain Python list. This is intentional for a demo.
- **No auth.** CORS is set to `allow_origins=["*"]`. Not for production.
- **Rule-based first, LLM second.** The rule engine always runs; the LLM is a post-processing override, not the primary classifier. If the LLM call fails, the rule-based result is returned unchanged.
- **KSA-specific regulatory context.** The LLM system prompt and signal `law` fields reference KSA PDPL, NDMO, SAMA Cybersecurity Framework, NCA ECC-1:2018, NCA DCC-1:2022, KSA AML Law, and KSA Labour Law — not UAE/international frameworks.

## Frontend state

All scanned document state lives in `App.jsx` as `scannedDocs` (array). Tab navigation is index-based (0–4). Framework selection (`fw`) and framework definitions (`frameworks`) are passed as props down to each tab.

## Dependencies

**Backend:** fastapi, uvicorn, python-multipart, openpyxl, pandas, python-docx, PyPDF2, httpx, python-dotenv

**Frontend:** React 18, Vite 5 (no CSS framework, no component library — all styles are inline)
