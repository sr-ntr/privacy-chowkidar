"""voice.py - Bilingual Voice Assistant for Privacy Chowkidar.

Powered entirely by Sarvam AI:
- Speech-to-Text (STT): Sarvam Saaras model via client.speech_to_text.transcribe
  Accepts WAV bytes from st.audio_input. No PyAudio or Microphone class used.
- Text-to-Speech (TTS): Sarvam Bulbul model via client.text_to_speech.convert
  Returns WAV audio bytes to play via st.audio.
- Risk Summary via sarvam-105b-conversations for intelligent, context-aware summaries.

All audio processing is strictly in-memory. No files are written to disk.
"""

from __future__ import annotations
import base64
import io
import os
from typing import Any, Dict, List, Tuple


def _get_client():
    """Initialise and return a SarvamAI client using the SARVAM_API_KEY env var."""
    try:
        from sarvamai import SarvamAI
    except ImportError:
        return None, "Library 'sarvamai' is not installed. Please run: pip install sarvamai"

    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        return None, "SARVAM_API_KEY is not set. Please add it to your .env file."

    return SarvamAI(api_subscription_key=api_key), None


def transcribe_audio(audio_bytes: bytes, lang: str = "en") -> Tuple[str, str | None]:
    """Transcribe audio bytes using Sarvam Saaras STT model.

    Uses language codes 'hi-IN' for Hindi and 'en-IN' for English.
    Accepts raw WAV/WebM bytes from st.audio_input — no PyAudio or Microphone required.
    """
    if not audio_bytes:
        return "", None

    client, err = _get_client()
    if err:
        return "", err

    lang_code = "hi-IN" if lang == "hi" else "en-IN"

    try:
        response = client.speech_to_text.transcribe(
            file=("audio.wav", io.BytesIO(audio_bytes), "audio/wav"),
            model="saaras:v2",
            language_code=lang_code,
        )
        transcript = getattr(response, "transcript", "") or ""
        if not transcript.strip():
            msg = (
                "आवाज़ स्पष्ट नहीं थी या कोई आवाज़ नहीं मिली।"
                if lang == "hi"
                else "No speech detected. Please try speaking closer to the microphone."
            )
            return "", msg
        return transcript.strip(), None
    except Exception as e:
        err_str = str(e)
        msg = (
            f"सर्वम एसटीटी त्रुटि: {err_str}"
            if lang == "hi"
            else f"Sarvam STT error: {err_str}"
        )
        return "", msg


def build_spoken_summary(
    risk_level: str, findings: List[Dict[str, Any]], lang: str = "en"
) -> str:
    """Generate a bilingual spoken risk summary using Sarvam sarvam-105b-conversations.

    Falls back to a static template if the API is unavailable (no credits, no key, etc).
    """
    count = len(findings)
    types = list({f["type"] for f in findings})
    types_str = ", ".join(types[:3]) if types else "none"

    # Build the LLM prompt
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

    client, err = _get_client()
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
            pass  # Fall through to static template below

    # Static fallback if LLM is unavailable
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
    """Convert text to spoken audio bytes using Sarvam Bulbul TTS model.

    Returns WAV audio bytes (base64-decoded from the API response) suitable
    for direct playback via st.audio.
    """
    if not text:
        return None, "Empty text provided for TTS."

    client, err = _get_client()
    if err:
        return None, err

    # Pick natural-sounding speakers per language
    lang_code = "hi-IN" if lang == "hi" else "en-IN"
    speaker = "ritu_hi_conversation" if lang == "hi" else "ritu_en_edtech"

    try:
        response = client.text_to_speech.convert(
            text=text,
            language_code=lang_code,
            speaker=speaker,
            model="bulbul:v2",
            output_audio_codec="wav",
        )
        # response.audios is a list of base64-encoded audio strings
        if not response.audios:
            return None, "Sarvam TTS returned no audio."

        audio_b64 = response.audios[0]
        audio_bytes = base64.b64decode(audio_b64)
        return audio_bytes, None
    except Exception as e:
        return None, f"Sarvam TTS error: {str(e)}"
