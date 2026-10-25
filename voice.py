"""voice.py - Bilingual Voice Assistant for Privacy Chowkidar.

Powered entirely by Sarvam AI:
- Speech-to-Text (STT): Sarvam Saaras (saaras:v3) via REST API with requests
- Text-to-Speech (TTS): Sarvam Bulbul (bulbul:v3) via REST API with requests
- Risk summaries: sarvam-105b-conversations via SDK

All audio processing is strictly in-memory. No files are written to disk.
"""

from __future__ import annotations
import base64
import io
import os
from typing import Any, Dict, List, Tuple

import requests

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_STT_MODEL = "saaras:v3"
LANG_CODES = {"en": "en-IN", "hi": "hi-IN"}

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
TTS_MODEL = "bulbul:v3"
TTS_SPEAKER = "shubh"
TTS_LANG = {"en": "en-IN", "hi": "hi-IN"}


def _api_key() -> str | None:
    """Resolve SARVAM_API_KEY from Streamlit secrets (Cloud) or environment (.env / shell)."""
    try:
        import streamlit as st
        key = st.secrets.get("SARVAM_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("SARVAM_API_KEY")


def _get_sdk_client():
    """Initialise and return a SarvamAI SDK client."""
    try:
        from sarvamai import SarvamAI
    except ImportError:
        return None, "Library 'sarvamai' is not installed. Run: pip install sarvamai"

    key = _api_key()
    if not key:
        return None, "SARVAM_API_KEY is not set. Add it to .env or .streamlit/secrets.toml"

    return SarvamAI(api_subscription_key=key), None


def transcribe_audio(audio_bytes: bytes, lang: str = "en") -> Tuple[str, str | None]:
    """Transcribe audio bytes using Sarvam Saaras STT REST API (saaras:v3).

    Sends WAV bytes from st.audio_input directly to the REST endpoint
    using requests — bypasses SDK parameter naming issues entirely.
    No PyAudio or Microphone class required.
    """
    if not audio_bytes:
        return "", None

    key = _api_key()
    if not key:
        return "", "SARVAM_API_KEY is not set. Add it to .env or .streamlit/secrets.toml"

    try:
        resp = requests.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": key},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={
                "model": SARVAM_STT_MODEL,
                "mode": "transcribe",
                "language_code": LANG_CODES.get(lang, "en-IN"),
            },
            timeout=30,
        )

        if resp.status_code != 200:
            try:
                msg = resp.json()["error"]["message"]
            except Exception:
                msg = resp.text[:300]
            err = f"Sarvam STT error ({resp.status_code}): {msg}"
            return "", err

        transcript = resp.json().get("transcript", "").strip()
        if not transcript:
            msg = (
                "आवाज़ स्पष्ट नहीं थी या कोई आवाज़ नहीं मिली। दोबारा कोशिश करें।"
                if lang == "hi"
                else "No speech detected. Please try speaking closer to the microphone."
            )
            return "", msg
        return transcript, None

    except requests.Timeout:
        return "", "Sarvam STT request timed out. Check your connection and try again."
    except Exception as e:
        return "", f"Sarvam STT error: {str(e)}"


def build_spoken_summary(
    risk_level: str, findings: List[Dict[str, Any]], lang: str = "en"
) -> str:
    """Generate a bilingual spoken risk summary using sarvam-105b-conversations.

    Falls back to a static template if the API is unavailable.
    """
    count = len(findings)
    types = list({f["type"] for f in findings})
    types_str = ", ".join(types[:3]) if types else "none"

    if lang == "hi":
        system_prompt = (
            "You are a bilingual privacy assistant. "
            "Generate a short, clear 2-3 sentence Hindi spoken warning summary for the user. "
            "Be concise, natural, and plain-spoken — no markdown, no bullet points."
        )
        user_prompt = (
            f"जोखिम स्तर: {risk_level}. "
            f"कुल {count} संवेदनशील विवरण मिले, जिनमें शामिल हैं: {types_str}। "
            "इसके बारे में 2-3 वाक्यों में हिंदी में एक स्पष्ट बोली जाने वाली सुरक्षा चेतावनी दें।"
        )
    else:
        system_prompt = (
            "You are a privacy assistant. "
            "Generate a short, clear 2-3 sentence spoken warning summary in English. "
            "Be concise, natural, and plain-spoken — no markdown, no bullet points."
        )
        user_prompt = (
            f"Risk level: {risk_level}. "
            f"Found {count} sensitive items including: {types_str}. "
            "Give a 2-3 sentence spoken privacy warning summary."
        )

    client, err = _get_sdk_client()
    if not err and client:
        try:
            response = client.chat.completions(
                model="sarvam-105b-conversations",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=120,
                temperature=0.4,
            )
            summary = response.choices[0].message.content
            if summary and summary.strip():
                return summary.strip()
        except Exception:
            pass  # Fall through to static template

    # Static fallback
    if not findings:
        if lang == "hi":
            return "प्राइवेसी चौकीदार रिपोर्ट: कोई संवेदनशील डेटा नहीं मिला। यह प्रॉम्प्ट भेजना पूरी तरह सुरक्षित है।"
        return "Privacy Chowkidar report: No sensitive data detected. This prompt is safe to send."

    if lang == "hi":
        return (
            f"प्राइवेसी चेतावनी! जोखिम स्तर {risk_level} है। "
            f"कुल {count} संवेदनशील विवरण पाए गए जिनमें {types_str} शामिल हैं। "
            "कृपया बाहरी एआई को भेजने से पहले ऑटो-रीडैक्ट विकल्प चुनें।"
        )
    return (
        f"Privacy Alert. Overall risk level is {risk_level}. "
        f"Found {count} sensitive items including {types_str}. "
        "Please use auto-redact before submitting to any external AI."
    )


def text_to_speech(text: str, lang: str = "en") -> Tuple[bytes | None, str | None]:
    """Convert text to WAV audio bytes using Sarvam Bulbul TTS REST API (bulbul:v3).

    Tries both 'target_language_code' and 'language_code' field names since Sarvam
    docs use both in different places. Returns (wav_bytes, None) on success or
    (None, error_message) on failure. Text is capped at 2500 chars (v3 limit).
    """
    if not text:
        return None, "Empty text provided for TTS."

    key = _api_key()
    if not key:
        return None, "SARVAM_API_KEY is not set. Add it to .env or .streamlit/secrets.toml"

    lang_code = TTS_LANG.get(lang, "en-IN")
    text = text[:2500]  # bulbul:v3 per-request character limit

    last_error = ""
    for lang_field in ("target_language_code", "language_code"):
        try:
            resp = requests.post(
                SARVAM_TTS_URL,
                headers={"api-subscription-key": key},
                json={
                    "text": text,
                    lang_field: lang_code,
                    "model": TTS_MODEL,
                    "speaker": TTS_SPEAKER,
                    "pace": 1.0,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                audio_bytes = base64.b64decode(resp.json()["audios"][0])
                return audio_bytes, None

            try:
                last_error = resp.json()["error"]["message"]
            except Exception:
                last_error = resp.text[:300]

            # Only retry with the alternate field name if it looks like a field-name issue
            if "language" not in last_error.lower():
                break

        except requests.Timeout:
            return None, "Sarvam TTS request timed out. Check your connection."
        except Exception as e:
            return None, f"Sarvam TTS error: {str(e)}"

    return None, f"Sarvam TTS error: {last_error}"
