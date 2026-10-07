from app.main import context_signals, analyze_text


def test_context_matching_does_not_match_inside_words():
    signals = context_signals("The accountability report was sent successfully.")
    assert not any(s["keyword"] == "account" for s in signals)
    assert not any(s["keyword"] == "send" for s in signals)


def test_context_matching_still_detects_real_phrases():
    signals = context_signals("Please send the bank account details immediately.")
    keywords = {s["keyword"] for s in signals}
    assert {"send", "bank", "account", "immediately"}.issubset(keywords)


def test_low_risk_plain_text_stays_low():
    result = analyze_text("This document contains general project notes and architecture decisions.", "text")
    assert result["riskLevel"] == "LOW"
