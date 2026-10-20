# ObliGOT

### Partnership operations, obligations, and document intelligence

ObliGOT is a partnership management platform created for the **Tata STRIVE Code Odyssey 5.0 hackathon**. It brings partner relationships, opportunities, agreements, programmes, financial records, and reporting obligations into one workspace—then highlights what needs attention, why it matters, and what to do next.

> **Project status:** Hackathon prototype. Validate configuration, data, authorization, and operational workflows before using it for production or real partner commitments.

<p align="center">
  <img alt="React" src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=20232A">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white">
  <img alt="Vite" src="https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="Firebase" src="https://img.shields.io/badge/Firebase-Auth%20%2B%20Admin-FFCA28?logo=firebase&logoColor=20232A">
  <img alt="Firestore" src="https://img.shields.io/badge/Cloud-Firestore-FFCA28?logo=googlecloud&logoColor=20232A">
  <img alt="Gemini" src="https://img.shields.io/badge/AI-Gemini-8E75B2?logo=googlegemini&logoColor=white">
  <img alt="Groq" src="https://img.shields.io/badge/AI-Groq-F55036?logo=groq&logoColor=white">
</p>

## What ObliGOT does

Partnership teams often track MOUs, opportunities, programme delivery, invoices, reports, and follow-ups in separate spreadsheets. ObliGOT provides a shared operational view and a document workflow that turns agreements into evidence-linked, editable spreadsheet output.

The system is designed around a clear division of responsibility:

- **Deterministic code** evaluates dates, deadlines, statuses, alert priorities, and arithmetic.
- **AI** assists with document reading and contextual recommendations; its output is advisory and may fail.
- **People** review the evidence, decide how to respond to alerts, and manage operational records.

## Core capabilities

### Operational workspace

- **Dashboard:** portfolio summary and the highest-priority active alerts.
- **Action Center:** alert evidence, reasons, recommended next steps, and human review actions.
- **Partners and Pipeline:** partner records, opportunities, ownership, stages, and next steps.
- **Agreements and Projects:** agreement lifecycle and programme delivery records.
- **Reports & UCs:** reporting obligations and utilization-certificate tracking.
- **Import:** preview, validate, and explicitly confirm supported CSV/XLSX imports.

The API and data model also support finance records. There is currently **no standalone Finance page** in the frontend.

### Explainable alerts

Alerts are computed from current records rather than stored as fixed snapshots. Each alert includes evidence, why it matters, a recommended action, and a transparent priority breakdown. Examples include agreements approaching expiry, missing signed copies, overdue reports or milestones, and opportunities needing follow-up.

Alert IDs are stable for the same rule and record. Human decisions—such as acknowledging, deferring, dismissing, or creating a task—are persisted; updating the underlying record can cause the alert to be reevaluated. Business dates use **Asia/Kolkata**.

### MOU and addendum workbooks

1. Upload an MOU or addendum PDF.
2. PyMuPDF reads embedded text and renders pages when needed. Scanned pages can be read with configured AI vision or optional local OCR.
3. The extraction workflow proposes fields, clauses, obligations, financial terms, programme scope, and tables with source-page evidence.
4. Deterministic validation checks values and evidence against the supplied document text or page reading.
5. Download an editable, document-scoped Excel workbook containing extracted values and their supporting evidence.

Extraction is advisory: it does **not** automatically create or update operational records. Workbook edits are not synchronized back into ObliGOT. Addendum comparisons remain document-scoped rather than silently changing an agreement.

### AI recommendations

The alert recommendation endpoint uses Gemini when configured. Document reading and structured extraction use the configured provider path, with Gemini and Groq support; local OCR can provide an additional reading fallback when installed and enabled. Provider failures are surfaced, and deterministic alerts remain available without AI. No AI output should be treated as verified operational data without human review.

## Technology

| Layer               | Technologies                                                                               |
| ------------------- | ------------------------------------------------------------------------------------------ |
| Frontend            | React 18, TypeScript, Vite, React Router, Lucide, CSS                                      |
| Backend API         | Python, FastAPI, Pydantic                                                                  |
| Data                | Cloud Firestore through the Firebase Admin SDK                                             |
| Authentication      | Firebase Authentication in the browser; optional Firebase ID-token verification in FastAPI |
| Document processing | PyMuPDF, openpyxl, Gemini, Groq; optional RapidOCR/Tesseract                               |
| Testing             | pytest, TypeScript compiler, Vite production build                                         |

## Architecture

```mermaid
flowchart LR
    U[Team member] --> FE[React + Firebase Auth]
    FE -->|ID token + API request| API[FastAPI]
    API --> AUTH[Firebase Admin token verification]
    API --> RULES[Deterministic rules and validation]
    API --> DB[Firestore repository]
    API --> DOC[PDF extraction and workbook export]
    DOC --> AI[Gemini / Groq / optional OCR]
    AI --> DOC
    RULES --> FE
    DB --> FE
    DOC --> FE
```

- FastAPI is the only application backend; API routes are mounted under `/api`.
- The browser uses Firebase Authentication and calls FastAPI. It does not access Firestore directly.
- Firestore client rules deny direct browser reads and writes. Backend authorization is enforced by the API when `REQUIRE_FIREBASE_AUTH=true`.
- AI keys and Firebase Admin credentials belong in the backend environment or a secret manager—never in frontend variables or source control.

## Run locally

### Prerequisites

- Python 3.12 recommended
- Node.js and npm
- A Firebase project with Authentication and Cloud Firestore enabled for live use
- Gemini and/or Groq credentials for AI-powered workflows
- Optional: RapidOCR or Tesseract for local OCR

### Backend

From the repository root, in PowerShell:

```powershell
Set-Location backend
py -3.12 -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On macOS or Linux, run from `backend/`:

```bash
python3 -m venv .venv
cp .env.example .env
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs`, and health status is at `/api/health`.

### Frontend

In a second terminal:

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Checks

Run the backend tests:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q .\tests
```

Build and type-check the frontend:

```powershell
Set-Location frontend
npm run build
```

## API and project references

- API overview: [`docs/API_ENDPOINTS.md`](docs/API_ENDPOINTS.md)
- Workbook schema: [`docs/WORKBOOK_SCHEMA.md`](docs/WORKBOOK_SCHEMA.md)
- Backend API docs while running: `http://127.0.0.1:8000/docs`
