"""detectors.py - Sensitive Data Detectors and Redaction for Privacy Chowkidar.

Provides regex-based detection, validation (e.g. Luhn algorithm for cards),
bilingual threat explanations (English / Hindi), and safe text redaction.
Zero data persistence: all scanning and transformation happen purely in-memory.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple


def luhn_check(number_str: str) -> bool:
    """Validate a card number string using the Luhn algorithm."""
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for idx, digit in enumerate(reverse_digits):
        if idx % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0


# Detection rule definitions with bilingual explanations and remediation guidance
RULES = [
    {
        "type": "Private Key",
        "tag": "[PRIVATE_KEY_REDACTED]",
        "severity": "Critical",
        "regex": re.compile(
            r"-----BEGIN\s+(?:[A-Z\s]+)?PRIVATE\s+KEY-----[A-Za-z0-9+/=\s\r\n]+?-----END\s+(?:[A-Z\s]+)?PRIVATE\s+KEY-----",
            re.MULTILINE,
        ),
        "threat_en": "Cryptographic key leakage leading to total infrastructure compromise or impersonation.",
        "threat_hi": "क्रिप्टोग्राफिक कुंजी लीक होने से पूरा सिस्टम हैक या अनधिकृत नियंत्रण हो सकता है।",
        "action_en": "Never send private keys to any LLM. Rotate and revoke this key immediately.",
        "action_hi": "प्राइवेट कुंजी कभी भी एलएलएम को न भेजें। इसे तुरंत रद्द और रीसेट करें।",
        "mask": lambda val: "-----BEGIN PRIVATE KEY [REDACTED]-----",
    },
    {
        "type": "API Key / Token",
        "tag": "[API_KEY_REDACTED]",
        "severity": "Critical",
        "regex": re.compile(
            r"\b("
            r"sk-[a-zA-Z0-9\-_]{20,}|"
            r"sk-proj-[a-zA-Z0-9\-_]{20,}|"
            r"sk-ant-[a-zA-Z0-9\-_]{20,}|"
            r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}|"
            r"gh[pousr]_[A-Za-z0-9_]{36,255}|"
            r"AIza[0-9A-Za-z\-_]{35}|"
            r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}"
            r")\b"
        ),
        "threat_en": "Direct credential leakage leading to cloud bill shock, data breach, and account takeover.",
        "threat_hi": "क्रेडेंशियल लीक होने से क्लाउड खाता हैक, भारी बिल और डेटा चोरी का खतरा होता है।",
        "action_en": "Remove API keys before submitting. Use environment variables locally.",
        "action_hi": "भेजने से पहले एपीआई कुंजी हटाएं। इसे सुरक्षित एन्वायरमेंट वेरिएबल में रखें।",
        "mask": lambda val: val[:4] + "..." + val[-4:] if len(val) >= 8 else "****",
    },
    {
        "type": "Password Pattern",
        "tag": "[PASSWORD_REDACTED]",
        "severity": "Critical",
        "regex": re.compile(
            r"(?i)\b(password|passwd|pwd|secret_key|api_secret)\s*[:=]\s*([^\s,;\"'<>]{4,})",
        ),
        "threat_en": "Plaintext credential exposure enabling unauthorized access and credential stuffing.",
        "threat_hi": "प्लेनटेक्स्ट पासवर्ड सार्वजनिक होने से अनधिकृत पहुंच और खाता हैक का खतरा है।",
        "action_en": "Omit passwords from prompts; LLMs never need real passwords to assist.",
        "action_hi": "प्रॉम्प्ट से पासवर्ड हटाएं; एलएलएम को वास्तविक पासवर्ड की आवश्यकता कभी नहीं होती।",
        "mask": lambda val: re.sub(r"([:=]\s*)(.+)", r"\1********", val),
    },
    {
        "type": "Credit/Debit Card",
        "tag": "[CARD_REDACTED]",
        "severity": "Critical",
        "regex": re.compile(
            r"(?<!\d)(?:(?:\d{4}[-\s]?){3}\d{4}|\d{13,19})(?!\d)"
        ),
        "validator": lambda val: luhn_check(val),
        "threat_en": "Direct financial fraud, card skimming, and unapproved online transactions.",
        "threat_hi": "सीधे वित्तीय धोखाधड़ी, कार्ड क्लोनिंग और अनधिकृत लेन-देन का खतरा।",
        "action_en": "Strip payment card details. Use placeholder numbers like 4111-XXXX-XXXX-1111 for testing.",
        "action_hi": "कार्ड विवरण हटाएं। परीक्षण के लिए केवल डमी नंबरों का उपयोग करें।",
        "mask": lambda val: "XXXX-XXXX-XXXX-" + re.sub(r"\D", "", val)[-4:],
    },
    {
        "type": "Aadhaar",
        "tag": "[AADHAAR_REDACTED]",
        "severity": "High",
        "regex": re.compile(
            r"(?<!\d)(?:[2-9]\d{3}[-\s]?\d{4}[-\s]?\d{4})(?![-\s]?\d)"
        ),
        "validator": lambda val: len(re.sub(r"\D", "", val)) == 12,
        "threat_en": "Identity theft, unauthorized banking access, and impersonation across Indian services.",
        "threat_hi": "पहचान की चोरी, बैंकिंग धोखाधड़ी और सरकारी/निजी सेवाओं में दुरुपयोग का जोखिम।",
        "action_en": "Mask the first 8 digits or replace with dummy identifier before submission.",
        "action_hi": "पहले 8 अंक मास्क करें या डमी नंबर का प्रयोग करें।",
        "mask": lambda val: "XXXX XXXX " + re.sub(r"\D", "", val)[-4:],
    },
    {
        "type": "PAN",
        "tag": "[PAN_REDACTED]",
        "severity": "High",
        "regex": re.compile(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
        ),
        "threat_en": "Tax profile exposure, identity fraud, and malicious credit application filings.",
        "threat_hi": "आयकर प्रोफ़ाइल का दुरुपयोग, जाली पहचान और अनधिकृत ऋण आवेदन का खतरा।",
        "action_en": "Redact PAN or use mock alphanumeric format (e.g., ABCDE1234F).",
        "action_hi": "पैन नंबर हटाएं या काल्पनिक पैन प्रारूप का प्रयोग करें।",
        "mask": lambda val: val[:2] + "******" + val[-2:],
    },
    {
        "type": "Passport",
        "tag": "[PASSPORT_REDACTED]",
        "severity": "High",
        "regex": re.compile(
            r"\b[A-PR-WYa-pr-wy][1-9]\d{6}\b"
        ),
        "threat_en": "International identity theft, fraudulent travel bookings, and KYC impersonation.",
        "threat_hi": "अंतर्राष्ट्रीय पहचान चोरी, फर्जी यात्रा बुकिंग और केवाईसी जालसाजी।",
        "action_en": "Omit official passport numbers when generating summaries or letters.",
        "action_hi": "सारांश या पत्र तैयार करते समय पासपोर्ट संख्या न जोड़ें।",
        "mask": lambda val: val[0].upper() + "*****" + val[-2:],
    },
    {
        "type": "UPI ID",
        "tag": "[UPI_ID_REDACTED]",
        "severity": "High",
        "regex": re.compile(
            r"\b[a-zA-Z0-9.\-_]{2,64}@(okaxis|okhdfcbank|okicici|oksbi|paytm|ybl|axl|ibl|apl|upi|gpay|phonepe|ptaxis|pthdfc|ptsbi|icici|hdfcbank|sbi|postbank|barodampay|kotak)\b",
            re.IGNORECASE,
        ),
        "threat_en": "Spam payment requests, phishing attempts, and personal identity linkage.",
        "threat_hi": "भुगतान स्पैम, फ़िशिंग हमले और व्यक्तिगत पहचान उजागर होने का जोखिम।",
        "action_en": "Redact your VPA address or replace with user@upi.",
        "action_hi": "वीपीए पता हटाएं या उपयोगकर्ता@upi जैसे डमी पते से बदलें।",
        "mask": lambda val: (val.split("@")[0][:2] + "***@" + val.split("@")[1]) if "@" in val else "***@upi",
    },
    {
        "type": "Indian Mobile",
        "tag": "[PHONE_REDACTED]",
        "severity": "High",
        "regex": re.compile(
            r"(?<!\d)(?:\+91[\-\s]?|91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}(?!\d)"
        ),
        "validator": lambda val: len(re.sub(r"\D", "", val)) in (10, 11, 12),
        "threat_en": "SIM-swap vulnerabilities, spam/telemarketing lists, and targeted WhatsApp smishing.",
        "threat_hi": "सिम-स्वैप धोखाधड़ी, अनचाहे स्पैम कॉल और लक्षित फ़िशिंग संदेशों का जोखिम।",
        "action_en": "Use sample numbers (+91 98765 43210) instead of real phone numbers.",
        "action_hi": "असली फ़ोन नंबर के बजाय काल्पनिक नंबर का उपयोग करें।",
        "mask": lambda val: "+91 XXXXX " + re.sub(r"\D", "", val)[-4:],
    },
    {
        "type": "Email",
        "tag": "[EMAIL_REDACTED]",
        "severity": "Medium",
        "regex": re.compile(
            r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
        ),
        # Ensure it doesn't duplicate UPI if captured
        "validator": lambda val: not re.search(
            r"@(okaxis|okhdfcbank|okicici|oksbi|paytm|ybl|axl|ibl|apl|upi|gpay|phonepe)\b",
            val,
            re.I,
        ),
        "threat_en": "Targeted spear-phishing, credential harvesting, and marketing data profiling.",
        "threat_hi": "लक्षित फ़िशिंग ईमेल, क्रेडेंशियल चोरी और अनचाहा प्रोफाइलिंग।",
        "action_en": "Use generic email address (e.g. user@example.com).",
        "action_hi": "सामान्य डमी ईमेल (उदा. user@example.com) का उपयोग करें।",
        "mask": lambda val: val[:2] + "***@" + val.split("@")[-1] if "@" in val else "***@***",
    },
    {
        "type": "IFSC Code",
        "tag": "[IFSC_REDACTED]",
        "severity": "Medium",
        "regex": re.compile(
            r"\b[A-Z]{4}0[A-Z0-9]{6}\b"
        ),
        "threat_en": "Pinpoints exact bank branch and geographical location, aiding financial recon.",
        "threat_hi": "सटीक बैंक शाखा और भौगोलिक स्थान का खुलासा, जिससे वित्तीय निगरानी आसान होती है।",
        "action_en": "Replace with generic branch code if not strictly needed.",
        "action_hi": "आवश्यक न होने पर इसे सामान्य शाखा कोड से बदलें।",
        "mask": lambda val: val[:4] + "0******",
    },
    {
        "type": "IP Address",
        "tag": "[IP_ADDRESS_REDACTED]",
        "severity": "Medium",
        "regex": re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        ),
        "threat_en": "Internal network topology mapping, server reconnaissance, and geo-location exposure.",
        "threat_hi": "नेटवर्क मैपिंग, सर्वर की जासूसी और स्थान की जानकारी उजागर होना।",
        "action_en": "Use RFC 5737 documentation IPs (e.g., 192.0.2.1) or internal placeholders.",
        "action_hi": "परीक्षण के लिए दस्तावेज़ीकरण आईपी (उदा. 192.0.2.1) का उपयोग करें।",
        "mask": lambda val: val.rsplit(".", 1)[0] + ".***",
    },
    {
        "type": "Context Keyword",
        "tag": "[CONTEXT_FLAGGED]",
        "severity": "Low",
        "regex": re.compile(
            r"(?i)\b(confidential|strictly\s+private|internal\s+use\s+only|nda\s+protected|"
            r"salary|compensation|annual\s+ctc|bank\s+statement|diagnosis|medical\s+history|"
            r"patient\s+record|termination\s+notice|trade\s+secret)\b"
        ),
        "threat_en": "Prompt context indicates corporate or medical sensitivity subject to NDA or HIPAA/GDPR.",
        "threat_hi": "गोपनीय व्यावसायिक या चिकित्सा डेटा जो एनडीए या डेटा सुरक्षा कानूनों के अधीन हो सकता है।",
        "action_en": "Verify that your organization permits sharing this context with external AI providers.",
        "action_hi": "पुष्टि करें कि आपका संगठन इस गोपनीय डेटा को बाहरी एआई के साथ साझा करने की अनुमति देता है।",
        "mask": lambda val: f"[Context: {val}]",
    },
]

SEVERITY_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


def scan_text(text: str) -> List[Dict[str, Any]]:
    """Scan input text for sensitive patterns and return a list of findings."""
    if not text or not isinstance(text, str):
        return []

    raw_findings: List[Dict[str, Any]] = []

    for rule in RULES:
        for match in rule["regex"].finditer(text):
            val = match.group(0)
            validator = rule.get("validator")
            if validator and not validator(val):
                continue

            start, end = match.start(), match.end()
            mask_fn = rule.get("mask", lambda v: "****")
            masked_preview = mask_fn(val)

            raw_findings.append({
                "type": rule["type"],
                "value": val,
                "start": start,
                "end": end,
                "severity": rule["severity"],
                "tag": rule["tag"],
                "masked": masked_preview,
                "threat_en": rule["threat_en"],
                "threat_hi": rule["threat_hi"],
                "action_en": rule["action_en"],
                "action_hi": rule["action_hi"],
            })

    # Deduplicate / resolve overlaps
    # Sort primarily by start asc, length desc, severity desc
    raw_findings.sort(
        key=lambda f: (
            f["start"],
            -(f["end"] - f["start"]),
            -SEVERITY_ORDER.get(f["severity"], 0),
        )
    )

    resolved: List[Dict[str, Any]] = []
    last_end = -1

    for finding in raw_findings:
        # If this finding starts before the previous resolved finding ended, resolve conflict
        if finding["start"] < last_end:
            prev = resolved[-1]
            prev_sev = SEVERITY_ORDER.get(prev["severity"], 0)
            curr_sev = SEVERITY_ORDER.get(finding["severity"], 0)

            # If current finding has strictly higher severity, replace previous
            if curr_sev > prev_sev:
                resolved.pop()
                resolved.append(finding)
                last_end = finding["end"]
            # Otherwise skip overlapping match
            continue

        resolved.append(finding)
        last_end = finding["end"]

    return resolved


def redact(text: str, findings: List[Dict[str, Any]] | None = None) -> str:
    """Redact sensitive findings from text, replacing them with safe tags.

    Context keywords are left intact with tags optional, while PII/secrets
    are substituted with their corresponding redaction tags.
    """
    if not text:
        return ""

    if findings is None:
        findings = scan_text(text)

    if not findings:
        return text

    # Sort findings by start descending so replacing indices doesn't offset subsequent indices
    sorted_findings = sorted(findings, key=lambda f: f["start"], reverse=True)
    redacted = text

    for f in sorted_findings:
        # Context keywords are informational alerts; we do not mangle the prompt for low context
        if f["severity"] == "Low":
            continue
        start, end = f["start"], f["end"]
        redacted = redacted[:start] + f["tag"] + redacted[end:]

    return redacted


def calculate_risk_level(findings: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    """Calculate overall risk meter based on findings severity and frequency.

    Returns:
        (risk_level, color_hex, risk_title)
    """
    if not findings:
        return ("Low", "#28a745", "Safe / सुरक्षित")

    max_severity = max(
        (SEVERITY_ORDER.get(f["severity"], 1) for f in findings), default=1
    )
    count = len(findings)

    if max_severity >= 4 or (max_severity >= 3 and count >= 3):
        return ("Critical", "#dc3545", "Critical Risk / गंभीर जोखिम")
    elif max_severity == 3:
        return ("High", "#fd7e14", "High Risk / उच्च जोखिम")
    elif max_severity == 2 or count >= 2:
        return ("Medium", "#ffc107", "Medium Risk / मध्यम जोखिम")
    else:
        return ("Low", "#17a2b8", "Low Risk / कम जोखिम")
