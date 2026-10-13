from __future__ import annotations

import base64
import io
import ipaddress
import os
import re
import shutil
from typing import Any
from urllib.parse import urlparse

from docx import Document
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import spacy
from spacy.matcher import Matcher
from PIL import Image
import pytesseract
from pytesseract import Output
import fitz
import json
from pathlib import Path

import joblib


def configure_tesseract() -> None:
    configured = os.environ.get("TESSERACT_CMD")
    if configured:
        pytesseract.pytesseract.tesseract_cmd = configured
    elif not shutil.which("tesseract") and os.name == "nt":
        for root in (os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
            if not root:
                continue
            for folder in ("Tesseract-OCR", "Programs/Tesseract-OCR"):
                candidate = Path(root) / folder / "tesseract.exe"
                if candidate.is_file():
                    pytesseract.pytesseract.tesseract_cmd = str(candidate)
                    return


configure_tesseract()

app = FastAPI(title="Privacy Risk ML Service", version="1.1.0")

# These are intentionally transparent recognizers. They are complemented by an ML classifier
# over extracted features, matching the project's two-stage design.
PATTERNS: list[tuple[str, str, float, str]] = [
    ("UPI_ID", r"(?i)(?<![\w.])[a-z0-9._-]{2,}@(oksbi|okaxis|okicici|okhdfcbank|ybl|ibl|axl|paytm|upi|apl|sbi|icici|hdfcbank|axisbank)(?![\w.])", 0.95, "financial identifier"),
    ("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0.99, "contact identity"),
    ("PHONE", r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)", 0.96, "phone number"),
    ("AADHAAR", r"(?<!\d)\d{4}[\s-]\d{4}[\s-]\d{4}(?!\d)", 0.94, "government identifier"),
    ("PAN", r"\b[A-Z]{5}\d{4}[A-Z]\b", 0.96, "government identifier"),
    ("IFSC", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", 0.96, "banking identifier"),
    ("GSTIN", r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b", 0.95, "tax/government identifier"),
    
    
    
    ("CARD", r"\b(?:\d[ -]*?){13,19}\b", 0.82, "financial identifier"),
    ("BANK_ACCOUNT", r"(?i)\b(?:account|a/c|acct|bank account)[\s:#-]*\d{8,18}\b", 0.92, "financial identifier"),
    ("IP_ADDRESS", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", 0.98, "network identifier"),
    ("DOB", r"\b(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]\d{2,4}\b", 0.83, "date of birth"),
    ("OTP", r"(?i)\b(?:otp|one[- ]time password|verification code)[\s:#-]*\d{4,8}\b", 0.98, "authentication secret"),
    ("PASSWORD", r"(?i)\b(?:password|passwd|pwd|passcode)[\s:#=]+[^\s,;]{4,}\b", 0.98, "authentication secret"),
]

SENSITIVE_CONTEXT = {
    "aadhaar": ("Government identifier is explicitly referenced", 20, "government_id"),
    "uidai": ("Government identity-service context detected", 18, "government_id"),
    "pan": ("Tax/government identifier is explicitly referenced", 18, "government_id"),
    "bank": ("Banking/financial information is referenced", 18, "financial"),
    "account": ("Financial/account information context detected", 12, "financial"),
    "otp": ("One-time authentication information is requested", 25, "authentication"),
    "password": ("Credential/password information is requested", 30, "authentication"),
    "verification": ("Identity or account verification context detected", 8, "context"),
    "upload": ("Explicit upload/data-sharing request detected", 7, "sharing_request"),
    "send": ("Explicit send/data-sharing request detected", 5, "sharing_request"),
    "share": ("Explicit sharing request detected", 5, "sharing_request"),
    "provide": ("Explicit request to provide information detected", 5, "sharing_request"),
    "submit": ("Explicit submission request detected", 5, "sharing_request"),
    "urgent": ("Urgency language may increase social-engineering risk", 8, "urgency"),
    "immediately": ("Immediate-action language may increase social-engineering risk", 8, "urgency"),
    "act now": ("Immediate-action language may increase social-engineering risk", 8, "urgency"),
    "verify now": ("Immediate verification language detected", 8, "urgency"),
}

FEATURE_NAMES = [
    "sensitive_element_count", "distinct_sensitive_types", "authentication_count",
    "financial_count", "government_identifier_count", "context_keyword_hits",
    "urgency_signal",
]


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODEL_DIR / "privacy_risk_model.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"
if not MODEL_PATH.exists():
    raise RuntimeError("Trained privacy-risk model is missing. Build the ML image so scripts/train_model.py runs first.")
# Persisted classifier and benchmark metadata
classifier = joblib.load(MODEL_PATH)
model_metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8")) if METADATA_PATH.exists() else {}

# Lightweight spaCy NLP layer for contextual entities. The application can later swap this
# matcher/rule layer for a trained transformer NER model without changing the API contract.
nlp = spacy.blank("en")
matcher = Matcher(nlp.vocab)
matcher.add("PERSON_CONTEXT", [[{"LOWER": {"IN": ["name", "called"]}}, {"LOWER": "is", "OP": "?"}, {"IS_ALPHA": True, "IS_TITLE": True}]])

class AnalyzeRequest(BaseModel):
    text: str | None = Field(default=None, max_length=150_000)
    sourceType: str = "text"
    url: str | None = None
    contentBase64: str | None = None
    filename: str | None = None
    mimeType: str | None = None
    redactionMode: str = "tagged"


def _ocr_image(image: Image.Image) -> tuple[str, float]:
    """Run local Tesseract OCR and return text plus mean word confidence."""
    # Discover installations added after the development server started.
    configure_tesseract()
    try:
        data = pytesseract.image_to_data(image, output_type=Output.DICT, config="--psm 6", timeout=20)
    except pytesseract.TesseractNotFoundError as exc:
        raise HTTPException(503, "OCR is unavailable. Install Tesseract OCR and add it to PATH or set TESSERACT_CMD to its executable, then restart the ML service.") from exc
    except pytesseract.TesseractError as exc:
        raise HTTPException(503, "OCR engine failed. Check the Tesseract installation and language data.") from exc
    except RuntimeError as exc:
        raise HTTPException(504, "OCR timed out. Try a smaller or clearer image.") from exc
    words: list[str] = []
    confidences: list[float] = []
    for word, raw_conf in zip(data.get("text", []), data.get("conf", [])):
        word = (word or "").strip()
        try:
            conf = float(raw_conf)
        except (TypeError, ValueError):
            conf = -1
        if word and conf >= 0:
            words.append(word)
            confidences.append(conf)
    return " ".join(words), (sum(confidences) / len(confidences) / 100.0 if confidences else 0.0)


def _ocr_pdf_page(page: fitz.Page) -> tuple[str, float]:
    """Render a scanned PDF page and OCR the rendered image."""
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return _ocr_image(image)


def extract_document(req: AnalyzeRequest) -> tuple[str, dict[str, Any]]:
    if not req.contentBase64:
        return req.text or "", {"extractionMethod": "text", "ocrUsed": False, "pages": []}
    try:
        raw = base64.b64decode(req.contentBase64, validate=True)
    except Exception as exc:
        raise HTTPException(400, "Invalid document encoding") from exc
    mime = req.mimeType or ""
    if mime in {"text/plain", "text/csv", "application/json"}:
        return raw.decode("utf-8", errors="replace")[:150_000], {"extractionMethod": "native_text", "ocrUsed": False, "pages": []}
    if mime == "application/pdf":
        try:
            pdf = fitz.open(stream=raw, filetype="pdf")
            chunks: list[str] = []
            pages: list[dict[str, Any]] = []
            ocr_used = False
            for index, page in enumerate(pdf):
                native = (page.get_text("text") or "").strip()
                # A scanned page often has little/no text layer. OCR only those pages.
                if len(native) >= 20:
                    text = native
                    method = "native_text"
                    confidence = None
                else:
                    text, confidence = _ocr_pdf_page(page)
                    method = "ocr"
                    ocr_used = True
                if text.strip():
                    chunks.append(f"[Page {index + 1}]\n{text}")
                page_info: dict[str, Any] = {"page": index + 1, "method": method, "characters": len(text)}
                if confidence is not None:
                    page_info["ocrConfidence"] = round(confidence, 3)
                pages.append(page_info)
            pdf.close()
            return "\n\n".join(chunks)[:150_000], {
                "extractionMethod": "hybrid_pdf", "ocrUsed": ocr_used, "pages": pages
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(400, "Unable to read PDF or run OCR") from exc
    if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)[:150_000], {"extractionMethod": "docx_text", "ocrUsed": False, "pages": []}
    if mime in {"image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"}:
        try:
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            text, confidence = _ocr_image(image)
            return text[:150_000], {
                "extractionMethod": "ocr_image",
                "ocrUsed": True,
                "pages": [{"page": 1, "method": "ocr", "characters": len(text), "ocrConfidence": round(confidence, 3)}],
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(400, "Unable to read image. Upload a valid PNG, JPEG, WEBP, BMP, or TIFF file.") from exc
    raise HTTPException(415, "Unsupported document type")


def mask(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * max(2, len(value) - 4) + value[-2:]


def valid_ip(value: str) -> bool:
    try:
        return all(int(part) <= 255 for part in value.split('.')) and ipaddress.ip_address(value).version == 4
    except Exception:
        return False


def detect(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    # NLP contextual detection. Regex recognizers below handle high-value structured PII.
    doc = nlp(text)
    address_match = re.search(r"(?i)\baddress(?:\s+is|\s*:)\s+([^\n.]{5,100})", text)
    if address_match:
        value = address_match.group(1).strip(" ,;:")
        findings.append({"type": "ADDRESS", "valueMasked": mask(value), "start": address_match.start(1), "end": address_match.end(1), "confidence": 0.76, "severity": "MEDIUM"})

    for match_id, start, end in matcher(doc):
        label = nlp.vocab.strings[match_id]
        span = doc[start:end]
        value = span.text
        if label == "PERSON_CONTEXT" and len(span) >= 2:
            # Skip the trigger token and keep the detected name token.
            name_token = span[-1]
            findings.append({"type": "NAME", "valueMasked": mask(name_token.text), "start": name_token.idx, "end": name_token.idx + len(name_token.text), "confidence": 0.80, "severity": "MEDIUM"})
    occupied: list[tuple[int,int]] = []
    # Context-gated Indian identifiers reduce false positives for formats that are too broad
    # to recognize safely without a nearby label.
    contextual_patterns = [
        ("AADHAAR", r"(?i)\b(?:aadhaar|uidai)[\s:#-]{0,8}(\d{12})\b", 0.94),
        ("VOTER_ID", r"(?i)\b(?:voter id|epic)[\s:#-]{0,8}([A-Z]{3}[0-9]{7})\b", 0.91),
        ("PASSPORT", r"(?i)\bpassport[\s:#-]{0,8}([A-Z][0-9]{7})\b", 0.94),
        ("DRIVING_LICENSE", r"(?i)\b(?:driving license|driver.?s license|dl)[\s:#-]{0,8}([A-Z]{2}[0-9]{2}[\s-]?[A-Z0-9]{8,13})\b", 0.89),
    ]
    for typ, pattern, confidence in contextual_patterns:
        for match in re.finditer(pattern, text):
            start, end = match.start(1), match.end(1)
            if any(start < e and end > st for st, e in occupied):
                continue
            value = match.group(1)
            findings.append({"type": typ, "valueMasked": mask(value), "start": start, "end": end, "confidence": confidence, "severity": "HIGH"})
            occupied.append((start, end))
    for typ, pattern, confidence, _ in PATTERNS:
        for match in re.finditer(pattern, text):
            value = match.group(0)
            if typ == "IP_ADDRESS" and not valid_ip(value):
                continue
            if any(match.start() < e and match.end() > s for s, e in occupied):
                continue
            severity = "HIGH" if typ in {"PASSWORD", "OTP", "CARD", "AADHAAR", "PAN", "BANK_ACCOUNT", "UPI_ID", "IFSC", "GSTIN", "VOTER_ID", "PASSPORT", "DRIVING_LICENSE"} else "MEDIUM"
            findings.append({"type": typ, "valueMasked": mask(value), "start": match.start(), "end": match.end(), "confidence": confidence, "severity": severity})
            occupied.append((match.start(), match.end()))
    findings.sort(key=lambda x: x["start"])
    return findings


def mask_character(value: str, finding_type: str) -> str:
    val = value.strip()
    if finding_type == "EMAIL" and "@" in val:
        user_part, domain = val.split("@", 1)
        visible_len = 3 if len(user_part) >= 6 else (2 if len(user_part) >= 4 else 1)
        masked_user = user_part[:visible_len] + "*" * max(3, len(user_part) - visible_len)
        return f"{masked_user}@{domain}"
    if finding_type == "AADHAAR":
        digits = [c for c in val if c.isdigit()]
        if len(digits) == 12:
            sep = "-" if "-" in val else " "
            return f"{''.join(digits[:4])}{sep}****{sep}****"
    if finding_type == "PHONE":
        digits = re.sub(r"\D", "", val)
        if len(digits) >= 10:
            prefix = "+91 " if "+91" in val else ""
            last10 = digits[-10:]
            return f"{prefix}{last10[:2]}******{last10[-2:]}"
    if finding_type == "CARD":
        digits = re.sub(r"\D", "", val)
        if len(digits) >= 12:
            return f"****-****-****-{digits[-4:]}"
    if finding_type == "PAN":
        if len(val) == 10:
            return f"{val[:2]}*****{val[-2:]}"
    if finding_type == "BANK_ACCOUNT":
        digits = re.sub(r"\D", "", val)
        if len(digits) >= 6:
            prefix = val[:val.find(digits[0])] if any(c.isdigit() for c in val) else ""
            return f"{prefix}******{digits[-4:]}"
    if len(val) <= 4:
        return "*" * len(val)
    return val[:2] + "*" * max(2, len(val) - 4) + val[-2:]

SYNTHETIC_REPLACEMENTS: dict[str, str] = {
    "EMAIL": "user.sample@example.com",
    "PHONE": "+91 9876543210",
    "AADHAAR": "9876 5432 1098",
    "PAN": "ABCDE1234F",
    "IFSC": "SBIN0001234",
    "UPI_ID": "user@oksbi",
    "CARD": "4111 1111 1111 1111",
    "BANK_ACCOUNT": "account 123456789012",
    "IP_ADDRESS": "192.0.2.1",
    "DOB": "01/01/1990",
    "OTP": "123456",
    "PASSWORD": "••••••••",
    "GSTIN": "27AAAAA0000A1Z5",
    "VOTER_ID": "ABC1234567",
    "PASSPORT": "Z1234567",
    "DRIVING_LICENSE": "DL01 20210001234",
    "NAME": "Alex Doe",
    "ADDRESS": "123 Sample Avenue, Suite 100",
}

def get_redacted_replacement(finding: dict[str, Any], text: str, mode: str = "tagged") -> str:
    start, end = finding["start"], finding["end"]
    val = text[start:end]
    f_type = finding.get("type", "SENSITIVE")
    if mode == "mask":
        return mask_character(val, f_type)
    elif mode == "synthetic":
        return SYNTHETIC_REPLACEMENTS.get(f_type, f"sample_{f_type.lower()}")
    elif mode == "blackout":
        length = max(4, min(len(val), 28))
        return "█" * length
    else:  # default 'tagged'
        return f"[{f_type} REDACTED]"

def redact(text: str, findings: list[dict[str, Any]], mode: str = "tagged") -> str:
    result = text
    for f in sorted(findings, key=lambda x: x["start"], reverse=True):
        replacement = get_redacted_replacement(f, text, mode)
        result = result[:f["start"]] + replacement + result[f["end"]:]
    return result[:150_000]

def all_redacted_variations(text: str, findings: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "tagged": redact(text, findings, "tagged"),
        "mask": redact(text, findings, "mask"),
        "synthetic": redact(text, findings, "synthetic"),
        "blackout": redact(text, findings, "blackout"),
    }


def context_signals(text: str) -> list[dict[str, Any]]:
    """Return contextual signals using word/phrase boundaries to reduce substring false positives."""
    signals: list[dict[str, Any]] = []
    for keyword, (label, weight, category) in SENSITIVE_CONTEXT.items():
        pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            signals.append({"keyword": keyword, "label": label, "weight": weight, "category": category})
    return signals


def feature_vector(text: str, findings: list[dict[str, Any]]) -> list[int]:
    counts = {typ: sum(1 for f in findings if f["type"] == typ) for typ, *_ in PATTERNS}
    for typ in ["NAME", "ADDRESS", "VOTER_ID", "PASSPORT", "DRIVING_LICENSE"]:
        counts[typ] = sum(1 for f in findings if f["type"] == typ)
    auth = counts["PASSWORD"] + counts["OTP"]
    financial = counts["CARD"] + counts["BANK_ACCOUNT"] + counts["UPI_ID"] + counts["IFSC"]
    government = counts["AADHAAR"] + counts["PAN"] + counts["GSTIN"] + counts["VOTER_ID"] + counts["PASSPORT"] + counts["DRIVING_LICENSE"]
    distinct = len({f["type"] for f in findings})
    signals = context_signals(text)
    context_hits = len(signals)
    urgency = int(any(s["category"] == "urgency" for s in signals))
    return [len(findings), distinct, auth, financial, government, context_hits, urgency]


def model_probability_score(probabilities: Any) -> float:
    labels = model_metadata.get("labels", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    weights = {"LOW": 10, "MEDIUM": 35, "HIGH": 65, "CRITICAL": 92}
    return sum(float(p) * weights.get(label, 50) for label, p in zip(labels, probabilities))


def local_model_contributions(features: list[int], probabilities: Any) -> list[dict[str, Any]]:
    baseline = model_probability_score(probabilities)
    contributions: list[dict[str, Any]] = []
    for i, value in enumerate(features):
        if value == 0:
            continue
        ablated = features.copy()
        ablated[i] = 0
        ablated_prob = classifier.predict_proba([ablated])[0]
        delta = baseline - model_probability_score(ablated_prob)
        contributions.append({
            "feature": FEATURE_NAMES[i],
            "value": value,
            "impact": round(delta, 2),
            "direction": "increases risk" if delta >= 0 else "reduces risk",
        })
    return sorted(contributions, key=lambda x: abs(x["impact"]), reverse=True)


def analyze_text(text: str, source_type: str, redaction_mode: str = "tagged") -> dict[str, Any]:
    findings = detect(text)
    features = feature_vector(text, findings)
    signals = context_signals(text)
    prediction = int(classifier.predict([features])[0])
    probabilities = classifier.predict_proba([features])[0]
    labels = model_metadata.get("labels", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    probability_map = {label: round(float(probabilities[i]), 4) for i, label in enumerate(labels)}
    model_confidence = max(float(p) for p in probabilities)
    probability_score = model_probability_score(probabilities)
    context_score = min(25, sum(int(s["weight"]) for s in signals))
    score = min(100, round(probability_score + len(findings) * 2 + features[2] * 7 + features[3] * 5 + features[4] * 4 + context_score * 0.35))
    # Safety floors prevent a clearly dangerous combination from being understated by a statistical model.
    if features[2] > 0 and (features[3] > 0 or features[4] > 0):
        score = max(score, 85)
    if features[2] >= 2:
        score = max(score, 95)
    if features[4] >= 2 and features[2] == 0:
        score = max(score, 65)
    if prediction == 3 and features[2] > 0:
        score = max(score, 85)
    if score >= 85: level = "CRITICAL"
    elif score >= 65: level = "HIGH"
    elif score >= 35: level = "MEDIUM"
    else: level = "LOW"

    factors: list[str] = []
    for signal in signals:
        if signal["label"] not in factors:
            factors.append(signal["label"])
    if findings: factors.append(f"{len(findings)} sensitive data element(s) detected")
    if len({f['type'] for f in findings}) >= 3: factors.append("Multiple categories of sensitive data are present")
    if not factors: factors.append("No high-confidence sensitive data was detected")

    recommendations = []
    if findings: recommendations.append("Remove, mask, or redact unnecessary personal information before sharing.")
    if any(f["type"] in {"PASSWORD", "OTP"} for f in findings): recommendations.append("Never share passwords or one-time authentication codes with another person or untrusted service.")
    if any(f["type"] in {"AADHAAR", "PAN", "BANK_ACCOUNT", "CARD", "UPI_ID", "IFSC", "GSTIN", "VOTER_ID", "PASSPORT", "DRIVING_LICENSE"} for f in findings): recommendations.append("Verify the recipient and business purpose independently before sharing government or financial identifiers.")
    if any(s["category"] == "urgency" for s in signals): recommendations.append("Treat urgent requests for sensitive information as potentially suspicious and verify through an independent channel.")
    if source_type == "url": recommendations.append("Check the destination domain, HTTPS status, and legitimacy before entering personal data.")
    if not recommendations: recommendations.append("Continue minimizing personal information and only share what is necessary for the stated purpose.")

    contributions = local_model_contributions(features, probabilities)
    explanation = []
    for item in contributions[:4]:
        explanation.append(f"{item['feature'].replace('_', ' ').title()} ({item['value']}) {item['direction']} by {abs(item['impact']):.1f} score points in the model ablation analysis.")
    
    variations = all_redacted_variations(text, findings)
    primary_redacted = variations.get(redaction_mode, variations["tagged"])

    return {
        "riskLevel": level, "riskScore": score, "findings": findings, "factors": factors,
        "recommendations": recommendations, "redactedText": primary_redacted,
        "redactionMode": redaction_mode,
        "redactedVariations": variations,
        "explainability": {
            "model": model_metadata.get("model", "trained classifier"),
            "modelConfidence": round(model_confidence, 4),
            "modelProbabilities": probability_map,
            "contextScore": context_score,
            "contextSignals": signals,
            "featureContributions": contributions,
            "narrative": explanation,
        },
        "featureSummary": {"featureVector": features, "featureNames": FEATURE_NAMES, "detectedTypes": sorted({f['type'] for f in findings}), "model": model_metadata.get("model", "trained classifier"), "modelProbabilities": probability_map}
    }

@app.get('/health')
def health(): return {"status": "ok", "service": "privacy-risk-ml", "model": model_metadata.get("model", "unknown")}

@app.get('/model-info')
def model_info():
    return model_metadata

@app.post('/analyze')
def analyze(req: AnalyzeRequest):
    text, extraction = extract_document(req)
    if not text.strip() and req.url: text = req.url
    if not text.strip(): raise HTTPException(400, "No analyzable content provided")
    result = analyze_text(text, req.sourceType, req.redactionMode)
    result["documentIntelligence"] = extraction
    return result
