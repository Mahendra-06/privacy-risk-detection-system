# Model Card — Privacy Risk Detection System

## Purpose
Classify privacy exposure into LOW, MEDIUM, HIGH, or CRITICAL after structured PII and contextual indicators are extracted.

## Current ML pipeline
1. Structured PII recognition and contextual NLP extract privacy signals.
2. Seven numeric features are generated: finding count, distinct PII types, authentication count, financial count, government-ID count, contextual-language hits, and urgency.
3. Three supervised classifiers are trained and evaluated:
   - Logistic Regression — baseline
   - Random Forest
   - Gradient Boosting
4. The model with the best macro-F1 on the held-out test set is selected automatically.
5. The selected model is persisted as a versioned `joblib` artifact in the repository model directory.

## Benchmark dataset
- 1,200 labeled examples
- 300 examples per class: LOW, MEDIUM, HIGH, CRITICAL
- 80/20 stratified train/test split
- Fixed random seed: 42
- Dataset is **synthetically generated for academic benchmarking**. It is not a substitute for a real-world privacy corpus and should not be presented as externally validated data.

## Current benchmark results
| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
|---|---:|---:|---:|---:|
| Logistic Regression | 87.50% | 88.00% | 87.50% | 87.52% |
| Random Forest | 92.50% | 93.20% | 92.50% | 92.60% |
| Gradient Boosting | 93.33% | 93.81% | 93.33% | 93.40% |

The bundled model artifact is the selected model produced by the training pipeline. Check `services/ml/models/metadata.json` for the exact benchmark associated with the current artifact.

## Important interpretation
These metrics demonstrate that the training/evaluation pipeline works; they do **not** establish production-level accuracy. The next ML milestone is evaluation on a representative, independently labeled privacy-risk dataset.

## Safety and limitations
- The score is an automated privacy-risk assessment, not legal or compliance advice.
- Structured recognizers are intentionally transparent and complement the ML classifier.
- Region-specific Indian identifiers should be expanded and validated with representative data.
- OCR supports images and scanned PDF pages through local Tesseract. OCR confidence is an extraction-quality signal and does not guarantee complete PII detection.
- URL scanning analyzes the URL string rather than crawling or executing remote pages.
- Raw sensitive input should not be retained unless a feature explicitly requires it.


## Phase 2 additions

The detection layer now includes Indian-specific government and financial identifiers: Aadhaar, PAN, IFSC, UPI/VPA, GSTIN, Voter ID/EPIC, passport and driving licence formats. Context-gated patterns are used for broad formats such as Voter ID, passport and driving licence to reduce accidental matches.

The classifier continues to consume the same seven aggregate features, with Indian government identifiers contributing to the government feature and UPI/IFSC contributing to the financial feature. This preserves the model API while increasing detection coverage.


## Phase 3 Explainability Addendum

The service exposes class probabilities and model confidence, but these should be interpreted as model outputs rather than calibrated legal or compliance probabilities. Local feature contribution values are produced by feature-ablation analysis: each non-zero feature is set to zero and the change in the model-derived risk score is measured. This is a practical local explanation for the structured feature model, not a guarantee of causal influence.

Context signals are independently detected from the text and contribute to the final application risk score through transparent, bounded heuristics. They are shown to the user so that urgency, authentication requests, financial identifiers, government identifiers, and explicit sharing requests are understandable.
