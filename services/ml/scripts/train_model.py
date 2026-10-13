from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
DATA_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)
random.seed(42)
np.random.seed(42)

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
    financial = counts["CARD"] + counts["BANK_ACCOUNT"] + counts["UPI_ID"] + counts["IFSC"]
    government = counts["AADHAAR"] + counts["PAN"] + counts["GSTIN"] + counts["VOTER_ID"] + counts["PASSPORT"] + counts["DRIVING_LICENSE"]
    distinct = sum(v > 0 for v in counts.values())
    total = sum(counts.values())
    return [total, distinct, auth, financial, government, context_hits, urgency]


def risk_from_features(f: list[int]) -> int:
    total, distinct, auth, financial, government, context, urgency = f
    raw = total * 5 + distinct * 7 + auth * 18 + financial * 11 + government * 10 + context * 3 + urgency * 7
    if auth and (financial or government):
        raw += 25
    if auth >= 2:
        raw += 20
    if total == 0:
        return 0
    if raw >= 90:
        return 3
    if raw >= 55:
        return 2
    if raw >= 20:
        return 1
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
    if random.random() < 0.04 and f[0] > 0:
        label = max(0, min(3, label + random.choice([-1, 1])))
    return text, label, f


print("Step 1: Generating/verifying balanced dataset...")
dataset_file = DATA_DIR / "privacy_risk_dataset.csv"
if not dataset_file.exists():
    rows = []
    target = {0: 300, 1: 300, 2: 300, 3: 300}
    while any(target[k] > 0 for k in target):
        text, label, f = make_example()
        if target[label] <= 0:
            continue
        target[label] -= 1
        rows.append({"text": text, "risk_label": label, "risk_level": ["LOW", "MEDIUM", "HIGH", "CRITICAL"][label], "features": f})

    random.shuffle(rows)
    with dataset_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "risk_level", "finding_count", "distinct_pii_types", "authentication_count", "financial_count", "government_id_count", "context_hits", "urgency"])
        for row in rows:
            writer.writerow([row["text"], row["risk_level"], *row["features"]])

df = pd.read_csv(dataset_file)
numeric_feature_names = [
    "finding_count", "distinct_pii_types", "authentication_count",
    "financial_count", "government_id_count", "context_hits", "urgency"
]
X = df[numeric_feature_names].values
label_names = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
label_to_id = {name: i for i, name in enumerate(label_names)}
y = df["risk_level"].map(label_to_id).values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, stratify=y, random_state=42
)

print(f"Dataset size: {len(df)} (Train: {len(X_train)}, Test: {len(X_test)})")
print("\nStep 2: Training and comparing five machine learning classification models...")

# Reference models from Google Colab:
# Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, XGBoost
candidate_models = {
    "logistic_regression": Pipeline([
        ("scale", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=2000, random_state=42))
    ]),
    "decision_tree": DecisionTreeClassifier(max_depth=15, min_samples_leaf=2, random_state=42),
    "random_forest": RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=2, random_state=42),
    "gradient_boosting": GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42),
    "xgboost": XGBClassifier(
        n_estimators=150, max_depth=4, learning_rate=0.08,
        subsample=0.9, colsample_bytree=0.9,
        objective="multi:softprob", eval_metric="mlogloss",
        random_state=42, n_jobs=-1
    ),
}

comparison_results = {}
for name, model in candidate_models.items():
    print(f"  - Training {name}...")
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    comparison_results[name] = {
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "precision_macro": round(float(precision_score(y_test, pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_test, pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_test, pred, average="macro", zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_test, pred, labels=[0, 1, 2, 3]).tolist(),
        "classification_report": classification_report(
            y_test, pred, labels=[0, 1, 2, 3], target_names=label_names, zero_division=0
        ),
    }

comparison_table = pd.DataFrame([
    {
        "Model": name,
        "Accuracy": r["accuracy"],
        "Macro Precision": r["precision_macro"],
        "Macro Recall": r["recall_macro"],
        "Macro F1-Score": r["f1_macro"],
    }
    for name, r in comparison_results.items()
]).sort_values("Macro F1-Score", ascending=False).reset_index(drop=True)

print("\nModel Comparison Table (Held-Out Test Set):")
print(comparison_table.to_string(index=False))

# Select best model based on highest macro-F1 score and accuracy
best_model_name = max(comparison_results, key=lambda n: (comparison_results[n]["f1_macro"], comparison_results[n]["accuracy"]))
print(f"\nStep 3: Best performing model selected: '{best_model_name}' (Macro F1: {comparison_results[best_model_name]['f1_macro']})")

# Hyperparameter grids following the Colab reference
param_grids = {
    "logistic_regression": {
        "classifier__C": [0.1, 1.0, 10.0]
    },
    "decision_tree": {
        "max_depth": [8, 12, 16, None],
        "min_samples_leaf": [1, 2, 4]
    },
    "random_forest": {
        "n_estimators": [150, 200, 250],
        "max_depth": [8, 12, None],
        "min_samples_leaf": [1, 2]
    },
    "gradient_boosting": {
        "n_estimators": [100, 150],
        "learning_rate": [0.03, 0.05, 0.1],
        "max_depth": [2, 3]
    },
    "xgboost": {
        "n_estimators": [100, 200],
        "max_depth": [3, 4, 5],
        "learning_rate": [0.05, 0.1]
    }
}

print(f"\nStep 4: Running GridSearchCV hyperparameter tuning on '{best_model_name}'...")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
grid_search = GridSearchCV(
    candidate_models[best_model_name],
    param_grids[best_model_name],
    cv=cv,
    scoring="f1_macro",
    n_jobs=-1,
    refit=True,
)
grid_search.fit(X_train, y_train)
best_estimator = grid_search.best_estimator_
best_params = grid_search.best_params_
print(f"  Best Parameters: {best_params}")
print(f"  Best 5-Fold CV Macro F1: {round(grid_search.best_score_, 4)}")

# Final evaluation of the tuned best model
final_pred = best_estimator.predict(X_test)
final_metrics = {
    "accuracy": round(float(accuracy_score(y_test, final_pred)), 4),
    "precision_macro": round(float(precision_score(y_test, final_pred, average="macro", zero_division=0)), 4),
    "recall_macro": round(float(recall_score(y_test, final_pred, average="macro", zero_division=0)), 4),
    "f1_macro": round(float(f1_score(y_test, final_pred, average="macro", zero_division=0)), 4),
    "confusion_matrix": confusion_matrix(y_test, final_pred, labels=[0, 1, 2, 3]).tolist(),
    "classification_report": classification_report(
        y_test, final_pred, labels=[0, 1, 2, 3], target_names=label_names, zero_division=0
    ),
}

print("\nFinal Tuned Model Evaluation Metrics:")
print(f"  Accuracy       : {final_metrics['accuracy']:.4f}")
print(f"  Macro Precision: {final_metrics['precision_macro']:.4f}")
print(f"  Macro Recall   : {final_metrics['recall_macro']:.4f}")
print(f"  Macro F1-Score : {final_metrics['f1_macro']:.4f}")
print("\nClassification Report:\n" + final_metrics["classification_report"])

# Save best model artifact and metadata
print("\nStep 5: Persisting best model and metadata...")
model_artifact_path = MODEL_DIR / "privacy_risk_model.joblib"
joblib.dump(best_estimator, model_artifact_path)

metadata = {
    "model": best_model_name,
    "best_parameters": best_params,
    "labels": label_names,
    "features": numeric_feature_names,
    "dataset_size": len(df),
    "train_size": len(X_train),
    "test_size": len(X_test),
    "synthetic": True,
    "random_state": 42,
    "final_metrics": {
        "accuracy": final_metrics["accuracy"],
        "precision_macro": final_metrics["precision_macro"],
        "recall_macro": final_metrics["recall_macro"],
        "f1_macro": final_metrics["f1_macro"],
        "confusion_matrix": final_metrics["confusion_matrix"],
    },
    "comparison": {
        name: {k: v for k, v in r.items() if k != "classification_report"}
        for name, r in comparison_results.items()
    },
    "results": comparison_results,
}
(MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

print(f"Artifacts successfully saved:")
print(f"  - Model: {model_artifact_path}")
print(f"  - Metadata: {MODEL_DIR / 'metadata.json'}")
