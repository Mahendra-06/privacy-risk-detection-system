from app.main import analyze_text


def test_context_signals_are_exposed():
    result = analyze_text(
        "URGENT: upload Aadhaar 2345 6789 0123 and OTP 582941 immediately.",
        "text",
    )
    signals = result["explainability"]["contextSignals"]
    categories = {s["category"] for s in signals}
    assert "government_id" in categories
    assert "authentication" in categories
    assert "urgency" in categories
    assert result["explainability"]["contextScore"] > 0


def test_model_probabilities_sum_to_one():
    result = analyze_text("Contact me at user@example.com", "text")
    probabilities = result["explainability"]["modelProbabilities"]
    assert abs(sum(probabilities.values()) - 1.0) < 0.01
    assert 0 <= result["explainability"]["modelConfidence"] <= 1


def test_local_feature_contributions_exist_for_nonzero_features():
    result = analyze_text(
        "Send bank account 123456789012 and OTP 582941 immediately.",
        "text",
    )
    contributions = result["explainability"]["featureContributions"]
    names = {item["feature"] for item in contributions}
    assert "authentication_count" in names
    assert "financial_count" in names
    assert contributions == sorted(contributions, key=lambda x: abs(x["impact"]), reverse=True)


def test_plain_text_extraction_metadata():
    from app.main import AnalyzeRequest, extract_document
    text, metadata = extract_document(AnalyzeRequest(text="hello", sourceType="text"))
    assert text == "hello"
    assert metadata["ocrUsed"] is False


def test_image_ocr_path_is_available():
    from app.main import AnalyzeRequest, extract_document
    import base64, io
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (900, 180), "white")
    ImageDraw.Draw(image).text((30, 50), "Aadhaar 2345 6789 0123", fill="black")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    text, metadata = extract_document(AnalyzeRequest(contentBase64=base64.b64encode(buf.getvalue()).decode(), mimeType="image/png", sourceType="document"))
    assert metadata["ocrUsed"] is True
    assert metadata["pages"][0]["method"] == "ocr"
    assert isinstance(text, str)
