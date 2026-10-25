"""tests/test_detectors.py - Unit tests for sensitive data detectors and redaction."""

import pytest
from detectors import scan_text, redact, calculate_risk_level, luhn_check


def test_valid_and_invalid_aadhaar():
    """Verify Aadhaar detection on valid 12-digit formats and rejection on invalid lengths/prefixes."""
    valid_text = "Citizen UID: 5489 1234 5678 and raw: 987654321012."
    findings = scan_text(valid_text)
    aadhaar_findings = [f for f in findings if f["type"] == "Aadhaar"]
    assert len(aadhaar_findings) == 2
    assert aadhaar_findings[0]["masked"] == "XXXX XXXX 5678"
    assert aadhaar_findings[0]["severity"] == "High"

    # Aadhaar numbers cannot start with 0 or 1
    invalid_text = "Invalid numbers: 0123 4567 8901 and 1234 5678 9012 and 12345."
    findings_invalid = [f for f in scan_text(invalid_text) if f["type"] == "Aadhaar"]
    assert len(findings_invalid) == 0


def test_valid_and_invalid_pan():
    """Verify Indian PAN detection and masking."""
    text = "Valid PAN: ABCDE1234F. Invalid PAN: ABCD12345F or ABCDEF1234F or 12345ABCDE."
    findings = scan_text(text)
    pan_findings = [f for f in findings if f["type"] == "PAN"]
    assert len(pan_findings) == 1
    assert pan_findings[0]["value"] == "ABCDE1234F"
    assert pan_findings[0]["masked"] == "AB******4F"
    assert pan_findings[0]["severity"] == "High"


def test_valid_and_invalid_credit_card_luhn():
    """Verify credit card detection using the Luhn validation algorithm."""
    # 4532 0150 0000 0007 satisfies Luhn
    valid_card = "Payment card: 4532-0150-0000-0007."
    findings = scan_text(valid_card)
    card_findings = [f for f in findings if f["type"] == "Credit/Debit Card"]
    assert len(card_findings) == 1
    assert card_findings[0]["severity"] == "Critical"
    assert card_findings[0]["masked"] == "XXXX-XXXX-XXXX-0007"

    # 4532 0150 0000 0008 fails Luhn
    invalid_card = "Random digits: 4532-0150-0000-0008."
    invalid_findings = [f for f in scan_text(invalid_card) if f["type"] == "Credit/Debit Card"]
    assert len(invalid_findings) == 0


def test_indian_mobile_and_upi():
    """Verify detection of Indian mobile numbers and UPI handles."""
    text = "Call me at +91 9876543210 or send money to priya@okhdfcbank."
    findings = scan_text(text)

    types = {f["type"] for f in findings}
    assert "Indian Mobile" in types
    assert "UPI ID" in types

    mobile = next(f for f in findings if f["type"] == "Indian Mobile")
    assert mobile["masked"] == "+91 XXXXX 3210"

    upi = next(f for f in findings if f["type"] == "UPI ID")
    assert upi["masked"] == "pr***@okhdfcbank"


def test_credentials_api_keys_and_passwords():
    """Verify detection of API keys, tokens, and password declarations."""
    text = (
        "Config: sk-proj-1234567890123456789012345 and "
        "AWS: AKIAIOSFODNN7EXAMPLE and "
        "password: SuperSecretPassword99!"
    )
    findings = scan_text(text)
    types = {f["type"] for f in findings}
    assert "API Key / Token" in types
    assert "Password Pattern" in types

    for f in findings:
        assert f["severity"] == "Critical"


def test_redaction_engine():
    """Verify redaction replaces PII with tags while preserving non-sensitive text."""
    prompt = "Transfer from my account for Aadhaar 5489 1234 5678 with PAN ABCDE1234F."
    redacted = redact(prompt)
    assert "[AADHAAR_REDACTED]" in redacted
    assert "[PAN_REDACTED]" in redacted
    assert "5489 1234 5678" not in redacted
    assert "ABCDE1234F" not in redacted
    assert "Transfer from my account for" in redacted


def test_risk_level_calculation():
    """Verify overall risk level categorisation."""
    # Critical risk with API key or credit card
    findings_crit = scan_text("My key is sk-1234567890123456789012345")
    level, color, _ = calculate_risk_level(findings_crit)
    assert level == "Critical"
    assert color == "#dc3545"

    # High risk with PAN
    findings_high = scan_text("My PAN is ABCDE1234F")
    level, color, _ = calculate_risk_level(findings_high)
    assert level == "High"

    # Low risk / safe for benign prompt
    findings_safe = scan_text("Translate this recipe to French please.")
    level, color, _ = calculate_risk_level(findings_safe)
    assert level == "Low"


def test_empty_and_benign_inputs():
    """Verify handling of empty strings, whitespace, and clean inputs."""
    assert scan_text("") == []
    assert scan_text("   \n\t  ") == []
    assert redact("") == ""
    assert redact("Tell me a bedtime story about elephants.") == "Tell me a bedtime story about elephants."
