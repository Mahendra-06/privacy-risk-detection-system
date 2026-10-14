# Privacy Risk Detection System

ML-powered privacy analysis platform for detecting PII/sensitive information, classifying privacy exposure, explaining the result, and redacting detected data.

## Architecture

- `apps/web` — React + TypeScript + Vite + Tailwind CSS
- `apps/api` — Node.js + Express + TypeScript + JWT + MongoDB
- `services/ml` — Python + FastAPI + spaCy/regex recognizers + scikit-learn risk classifier

## Features

- JWT authentication and protected scan history
- Text scanning
- Document scanning for TXT, CSV, JSON, PDF and DOCX
- PII detection: email, phone, Aadhaar-like ID, PAN-like ID, bank account, card, IP, address/context, OTP/authentication context
- ML risk classification: LOW / MEDIUM / HIGH / CRITICAL
- Explainable factors and recommendations
- Automatic redaction
- Scan history and report detail
- Dashboard metrics
- No raw input is stored by default; only metadata, findings and redacted preview are retained

## Local development (no Docker)

### Requirements
Node.js 20+, Python 3.11+, MongoDB 7+, Tesseract OCR for image/scanned-PDF OCR.

### First-time setup
From the project root on Windows:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup-dev.ps1
```

Or manually:

```powershell
npm install
npm --prefix apps/api install
npm --prefix apps/web install
python -m pip install -r services/ml/requirements.txt
```

Make sure MongoDB is running locally on port `27017`. For OCR, install Tesseract and ensure `tesseract.exe` is available on PATH. Standard Windows Tesseract install locations are also detected automatically. For a custom location, set `$env:TESSERACT_CMD = 'C:\path\to\tesseract.exe'` in PowerShell before running `npm run dev`. Restart the ML service after installing or configuring Tesseract. Installing the Python `pytesseract` package alone does not install the OCR engine.

### Start the entire application

```powershell
npm run dev
```

This starts all three application services together:

- Frontend: `http://localhost:5173`
- API: `http://localhost:4000`
- ML service: `http://127.0.0.1:8000`
- MongoDB: `mongodb://127.0.0.1:27017/privacy_risk_detection_system`

Press `Ctrl+C` once to stop the development processes.

### Useful commands

```powershell
npm run test:ml
npm run build
```

## Phase 2 validation

The ML service test suite contains the Phase 2 detector tests covering legacy behavior, Indian financial identifiers, Indian government identifiers, contextual gating, critical-risk combinations, and redaction.


## Phase 3 — Contextual Risk Intelligence & Explainability

Phase 3 adds an explainability layer on top of the PII detector and trained classifier. Each analysis now returns:

- model confidence and per-class probabilities
- contextual risk signals (government ID, financial, authentication, sharing request, urgency)
- a capped context score
- local feature contributions calculated with model-ablation analysis
- a human-readable model narrative
- context-aware recommendations for urgent or suspicious requests

The API continues to treat the result as an automated risk assessment rather than a legal/compliance determination.

### Explainability flow

```text
PII / NER findings
       +
Context signals
       +
Feature vector
       ↓
Trained classifier
       ↓
Class probabilities
       ↓
Local feature ablation
       ↓
Risk score + explanation + recommendations
```

### Phase 3 tests

The ML service test suite covers the detector, explainability, OCR/document intelligence, and hardening behavior covering the original detector, Indian PII recognizers, context signals, probability normalization, local feature contributions, and redaction.


## Phase 4 — Document Intelligence and OCR

The document pipeline now supports native text extraction plus local OCR. TXT/CSV/JSON/DOCX continue to use native extraction. PDFs use a hybrid strategy: pages with a usable text layer are extracted directly, while pages with little/no text are rendered and passed through Tesseract OCR. PNG/JPEG/WEBP/BMP/TIFF uploads are OCR-scanned directly.

OCR metadata is returned in `documentIntelligence`, including extraction method, whether OCR was used, page count, per-page character count, and OCR confidence where available. The extracted text then enters the same PII detection, contextual feature extraction, Random Forest classification, explainability, and redaction pipeline as pasted text.

OCR confidence is an extraction-quality signal, not model confidence and not a guarantee that all PII was detected.

## Final validation and limitations

Before a production deployment, replace the development `JWT_SECRET`, restrict CORS to the deployed frontend origin, avoid exposing MongoDB directly to the public network, and configure TLS/reverse-proxy controls. The bundled ML benchmark uses synthetic data; its metrics should not be presented as real-world detection accuracy. OCR confidence measures extraction quality and does not guarantee complete PII detection. Model probabilities are classifier outputs and are not guaranteed to be calibrated probabilities. Local feature ablation explains how the trained model's score changes when an input feature is removed; it is not a causal explanation.

### Test command

```powershell
npm run test:ml
```

```bash
cd services/ml
PYTHONPATH=. pytest -q tests
```

The final validation suite covers detector behavior, Indian identifiers, contextual explainability, OCR extraction paths, redaction, and context-matching hardening.
