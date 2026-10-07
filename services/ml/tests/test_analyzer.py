from app.main import analyze_text

def test_low_risk_email():
    result = analyze_text("Contact me at user@example.com", "text")
    assert result["riskLevel"] in {"LOW", "MEDIUM"}
    assert any(x["type"] == "EMAIL" for x in result["findings"])

def test_critical_sensitive_request():
    result = analyze_text("Upload Aadhaar 1234 5678 9012, PAN ABCDE1234F and OTP 123456 immediately", "text")
    assert result["riskLevel"] == "CRITICAL"
    assert result["riskScore"] >= 85
    assert "authentication" in " ".join(result["factors"]).lower()

def test_redaction():
    result = analyze_text("email test@example.com", "text")
    assert "test@example.com" not in result["redactedText"]

def test_government_ids_are_high_not_critical_without_authentication():
    result = analyze_text("Please provide Aadhaar 2345 6789 0123 and PAN ABCDE1234F for verification.", "text")
    assert result["riskLevel"] == "HIGH"
    assert {f["type"] for f in result["findings"]} >= {"AADHAAR", "PAN"}


def test_authentication_plus_financial_is_critical():
    result = analyze_text("URGENT: send account 123456789012 and OTP 582941 immediately.", "text")
    assert result["riskLevel"] == "CRITICAL"
    assert {f["type"] for f in result["findings"]} >= {"BANK_ACCOUNT", "OTP"}

def test_indian_financial_identifiers():
    text = "UPI ID mahendra@oksbi, IFSC SBIN0001234, bank account 123456789012"
    result = analyze_text(text, "text")
    types = {f["type"] for f in result["findings"]}
    assert {"UPI_ID", "IFSC", "BANK_ACCOUNT"}.issubset(types)


def test_indian_government_identifiers():
    text = "GSTIN 37ABCDE1234F1Z5, Voter ID ABC1234567, passport A1234567, driving license AP01 20230012345"
    result = analyze_text(text, "text")
    types = {f["type"] for f in result["findings"]}
    assert {"GSTIN", "VOTER_ID", "PASSPORT", "DRIVING_LICENSE"}.issubset(types)


def test_unlabelled_voter_id_is_not_detected():
    result = analyze_text("Reference code ABC1234567", "text")
    assert not any(f["type"] == "VOTER_ID" for f in result["findings"])
