from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path

import joblib
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
DATA_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)
random.seed(42)

VALUES = {
    "name": ["Mahendra Kumar", "Anita Rao", "Rahul Sharma", "Priya Singh", "Arjun Reddy"],
    "email": ["user@example.com", "student@example.com", "contact@example.org", "demo.user@mail.com"],
    "phone": ["+91 9876543210", "+91 9123456789", "+91 9988776655"],
    "aadhaar": ["2345 6789 0123", "3456 7890 1234", "4567 8901 2345"],
    "pan": ["ABCDE1234F", "FGHIJ5678K", "LMNOP9012Q"],
    "bank": ["123456789012", "987654321098", "456789012345"],
    "card": ["4111111111111111", "5555555555554444"],
    "otp": ["482916", "582941", "728391", "839201"],
    "password": ["MySecretPass123", "SecurePwd456", "DemoPass789"],
    "ip": ["192.168.1.25", "10.0.0.42", "172.16.0.8"],
    "upi": ["mahendra@oksbi", "student@upi", "demo.user@icici"],
    "ifsc": ["SBIN0001234", "HDFC0001234", "ICIC0001234"],
    "gstin": ["37ABCDE1234F1Z5", "27FGHIJ5678K2Z6", "29LMNOP9012Q3Z7"],
    "voter": ["ABC1234567", "XYZ7654321", "QWE2468135"],
    "passport": ["A1234567", "K7654321", "M2468135"],
    "dl": ["AP01 20230012345", "TS09 20190067890", "KA05 20210054321"],
}

PII_SNIPPETS = {
    "EMAIL": "email {email}",
    "PHONE": "phone {phone}",
    "AADHAAR": "Aadhaar {aadhaar}",
    "PAN": "PAN {pan}",
    "BANK_ACCOUNT": "account {bank}",
    "CARD": "card {card}",
    "OTP": "OTP {otp}",
    "PASSWORD": "password {password}",
    "IP_ADDRESS": "IP address {ip}",
    "UPI_ID": "UPI ID {upi}",
    "IFSC": "IFSC {ifsc}",
    "GSTIN": "GSTIN {gstin}",
    "VOTER_ID": "Voter ID {voter}",
    "PASSPORT": "passport {passport}",
    "DRIVING_LICENSE": "driving license {dl}",
    "DOB": "date of birth 15/08/2004",
}

CONTEXTS = [
    "for the project record",
    "for registration",
    "for identity verification",
    "to process the refund",
    "to complete account verification",
    "because the account is being reviewed",
    "please share it",
    "please upload it",
    "send it immediately",
    "URGENT: provide it now",
]


def value(key: str) -> str:
    return random.choice(VALUES[key])


def render_snippet(kind: str) -> str:
    return PII_SNIPPETS[kind].format(**{k: value(k) for k in VALUES})


def feature_from_counts(counts: dict[str, int], context_hits: int, urgency: int) -> list[int]:
    auth = counts["PASSWORD"] + counts["OTP"]
    financial = counts["CARD"] + counts["BANK_ACCOUNT"]
    government = counts["AADHAAR"] + counts["PAN"]
    return [sum(counts.values()), sum(v > 0 for v in counts.values()), auth, financial, government, context_hits, urgency]


def risk_from_features(f: list[int]) -> int:
    total, distinct, auth, financial, government, context, urgency = f
    raw = total * 5 + distinct * 7 + auth * 18 + financial * 11 + government * 10 + context * 3 + urgency * 7
    if auth and (financial or government): raw += 25
    if auth >= 2: raw += 20
    if total == 0: return 0
    if raw >= 90: return 3
    if raw >= 55: return 2
    if raw >= 20: return 1
    return 0


def detect_counts(text: str) -> dict[str, int]:
    patterns = {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "PHONE": r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)",
        "AADHAAR": r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)|(?i:\b(?:aadhaar|uidai)[\s:#-]{0,8}\d{12}\b)",
        "PAN": r"\b[A-Z]{5}\d{4}[A-Z]\b",
        "CARD": r"\b(?:\d[ -]*?){13,19}\b",
        "BANK_ACCOUNT": r"(?i)\b(?:account|a/c|acct)[\s:#-]*\d{8,18}\b",
        "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "DOB": r"\b(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]\d{2,4}\b",
        "OTP": r"(?i)\b(?:otp|one[- ]time password|verification code)[\s:#-]*\d{4,8}\b",
        "PASSWORD": r"(?i)\b(?:password|passwd|pwd|passcode)[\s:#=]+[^\s,;]{4,}\b",
        "UPI_ID": r"(?i)(?<![\w.])[a-z0-9._-]{2,}@(oksbi|okaxis|okicici|okhdfcbank|ybl|ibl|axl|paytm|upi|apl|sbi|icici|hdfcbank|axisbank)(?![\w.])",
        "IFSC": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        "GSTIN": r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
        "VOTER_ID": r"(?i)\b(?:voter id|epic)[\s:#-]{0,8}[A-Z]{3}[0-9]{7}\b",
        "PASSPORT": r"(?i)\bpassport[\s:#-]{0,8}[A-Z][0-9]{7}\b",
        "DRIVING_LICENSE": r"(?i)\b(?:driving license|driver.?s license|dl)[\s:#-]{0,8}[A-Z]{2}[0-9]{2}[\s-]?[A-Z0-9]{8,13}\b",
    }
    return {k: len(re.findall(v, text)) for k, v in patterns.items()}


def make_example() -> tuple[str, int, list[int]]:
    kinds = list(PII_SNIPPETS)
    # Zero to four PII types, with extra weight on realistic combinations.
    n = random.choices([0, 1, 2, 3, 4], weights=[18, 28, 26, 20, 8])[0]
    selected = random.sample(kinds, n)
    snippets = [render_snippet(k) for k in selected]
    context = random.choice(CONTEXTS) if random.random() < 0.72 else "for reference"
    text = " ".join(snippets) if snippets else random.choice([
        "Hello, I am a computer science student working on a software project.",
        "Please review the project requirements and submit the assignment tomorrow.",
        "The application server is available for testing.",
    ])
    if snippets:
        text += " " + context + "."
    if random.random() < 0.18:
        text = "URGENT: " + text
    counts = detect_counts(text)
    context_hits = sum(1 for w in ["verification", "upload", "send", "share", "urgent", "immediately", "provide", "refund", "registration"] if w in text.lower())
    urgency = int(bool(re.search(r"(?i)urgent|immediately|now|today", text)))
    f = feature_from_counts(counts, context_hits, urgency)
    label = risk_from_features(f)
    # A small amount of label noise prevents the benchmark from becoming a deterministic rule table.
    if random.random() < 0.04 and f[0] > 0:
        label = max(0, min(3, label + random.choice([-1, 1])))
    return text, label, f


rows = []
# Keep classes reasonably balanced for a meaningful macro-F1 comparison.
target = {0: 300, 1: 300, 2: 300, 3: 300}
while any(target[k] > 0 for k in target):
    text, label, f = make_example()
    if target[label] <= 0:
        continue
    target[label] -= 1
    rows.append({"text": text, "risk_label": label, "risk_level": ["LOW", "MEDIUM", "HIGH", "CRITICAL"][label], "features": f})

random.shuffle(rows)
with (DATA_DIR / "privacy_risk_dataset.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["text", "risk_level", "finding_count", "distinct_pii_types", "authentication_count", "financial_count", "government_id_count", "context_hits", "urgency"])
    for row in rows:
        writer.writerow([row["text"], row["risk_level"], *row["features"]])

X = [row["features"] for row in rows]
y = [row["risk_label"] for row in rows]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=42)

models = {
    "logistic_regression": Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=2000, random_state=42))]),
    "random_forest": RandomForestClassifier(n_estimators=250, max_depth=8, min_samples_leaf=2, random_state=42),
    "gradient_boosting": GradientBoostingClassifier(n_estimators=150, learning_rate=0.05, max_depth=3, random_state=42),
}

results = {}
for name, model in models.items():
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    results[name] = {
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "precision_macro": round(precision_score(y_test, pred, average="macro", zero_division=0), 4),
        "recall_macro": round(recall_score(y_test, pred, average="macro", zero_division=0), 4),
        "f1_macro": round(f1_score(y_test, pred, average="macro", zero_division=0), 4),
        "confusion_matrix": confusion_matrix(y_test, pred, labels=[0, 1, 2, 3]).tolist(),
        "classification_report": classification_report(y_test, pred, labels=[0, 1, 2, 3], target_names=["LOW", "MEDIUM", "HIGH", "CRITICAL"], zero_division=0),
    }

best_name = max(results, key=lambda n: (results[n]["f1_macro"], results[n]["accuracy"]))
joblib.dump(models[best_name], MODEL_DIR / "privacy_risk_model.joblib")
metadata = {
    "model": best_name,
    "labels": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    "features": ["finding_count", "distinct_pii_types", "authentication_count", "financial_count", "government_id_count", "context_hits", "urgency"],
    "dataset_size": len(rows), "train_size": len(X_train), "test_size": len(X_test),
    "synthetic": True, "random_state": 42, "results": results,
}
(MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(json.dumps({"selected_model": best_name, "dataset_size": len(rows), "results": {k: {m: v for m, v in r.items() if m != "classification_report"} for k, r in results.items()}}, indent=2))
