# Client Data Classification Tool

Data discovery and governance demo for Client. Scans uploaded files, detects sensitive data using regex patterns and keyword dictionaries, classifies documents by type, maps to DDE and UAE Federal frameworks, and presents results in an interactive dashboard.

## Quick start

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev

# Or run both at once:
python run.py
```

Open **http://localhost:5173** and upload files from the `sample-files/` folder.

## Architecture

```
frontend/ (React + Vite, port 5173)
├── App.jsx              ← Shell, tabs, state
├── config.js            ← API URL, colors
├── components.jsx       ← Pill, SevBadge, SrcIcon, Card, etc.
└── tabs/
    ├── Upload.jsx       ← Drag-drop, per-file progress
    ├── Datasets.jsx     ← Structured data explorer (dynamic + static)
    ├── DocScan.jsx      ← Scan table (sort, filter)
    ├── DocDetail.jsx    ← Signal analysis + metadata
    └── ExecSummary.jsx  ← Charts, recommendations, export

backend/ (FastAPI, port 8000)
├── main.py              ← Routes: /api/scan, /api/frameworks, /api/export
├── pipeline.py          ← Orchestrator: extract → detect → classify → map
├── extractors.py        ← xlsx, csv, txt, docx, pdf
├── detectors.py         ← 20+ regex patterns, 18 keyword dicts, column matchers
├── engine.py            ← Doc-type classifier, 9 signal rules, scorer, redactor
├── frameworks.py        ← DDE + UAE Federal definitions, tier mapping
└── export.py            ← XLSX report generation
```

## Detection pipeline (per file)

```
Upload → Extractor (by file type)
       → Pattern detector (20+ regex: Emirates ID, IBAN, passport,
         visa, credit card, SWIFT, phone, email, trade licence,
         TRN, API keys, passwords, etc.)
       → Keyword detector (18 dictionaries: health, biometric,
         criminal, religious, ethnic, genetic, minors, AML/KYC,
         PEP, sanctions, strategic, employment, financial,
         security controls, legal privilege, governance, etc.)
       → Column detector (structured files: name-based + sample validation)
       → Document-type classifier (data file, policy, KYC, strategy, etc.)
       → Signal analysis (9 signals with co-occurrence + escalation)
       → Confidence scorer
       → Framework mapper (DDE + UAE Federal tier assignment)
       → JSON response
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/frameworks` | GET | Framework definitions (frontend reads these) |
| `/api/scan` | POST | Scan single file (multipart form) |
| `/api/scan-batch` | POST | Scan multiple files |
| `/api/export?framework=dde` | GET | Download XLSX report |
| `/api/results` | DELETE | Clear stored results |

## Frameworks

**DDE (Dubai Data Manual)**
- Open → Shared — confidential → Shared — sensitive → Shared — secret

**UAE Federal (TDRA)**
- Open → Confidential → Sensitive → Secret

## Sample files

| File | Type | Expected classification |
|------|------|----------------------|
| Employee_Salary_Q4_2025.xlsx | Data file | Sensitive / Critical |
| IT_Security_Policy_v3.2.txt | Policy document | Confidential / Medium |
| KYC_Customer_Due_Diligence_AcmeCorp.txt | KYC file | Sensitive / Critical |
| Training_Attendance_Feb2026.xlsx | Data file | Confidential / Medium |
| Vendor_Payment_Schedule_Q1.xlsx | Data file | Confidential / Medium |
| Trade_Licence_Registry.csv | Data file | Open / Low |
| Board_Strategy_Deck_2026.txt | Strategy document | Secret / High |
