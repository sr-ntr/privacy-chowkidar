"""voice.py - Bilingual Voice Assistant for Privacy Chowkidar.

Provides:
- Speech-to-Text (STT): st.audio_input WAV bytes -> SpeechRecognition.recognize_google
  (using language codes 'en-IN' and 'hi-IN'). Purely file/byte based; NO PyAudio / Microphone.
- Text-to-Speech (TTS): gTTS audio generation in English and Hindi playing via st.audio.
- In-memory execution without writing audio files to persistent storage.
"""

from __future__ import annotations
import io
from typing import Any, Dict, List, Tuple


def transcribe_audio(audio_bytes: bytes, lang: str = "en") -> Tuple[str, str | None]:
    """Transcribe audio bytes using SpeechRecognition's Google Web Speech API.

    Uses language codes 'en-IN' for English and 'hi-IN' for Hindi.
    Does NOT use PyAudio or Microphone class.
    """
    if not audio_bytes:
        return "", None

    try:
        import speech_recognition as sr
    except ImportError:
        return "", "Library 'SpeechRecognition' is not installed. Please run: pip install SpeechRecognition"

    recognizer = sr.Recognizer()
    lang_code = "hi-IN" if lang == "hi" else "en-IN"

    try:
        audio_stream = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_stream) as source:
            audio_data = recognizer.record(source)

        transcript = recognizer.recognize_google(audio_data, language=lang_code)
        return transcript.strip(), None
    except sr.UnknownValueError:
        msg = (
            "आवाज़ स्पष्ट नहीं थी या कोई आवाज़ नहीं मिली।"
            if lang == "hi"
            else "Audio could not be understood. Please try speaking closer to the microphone."
        )
        return "", msg
    except sr.RequestError as e:
        msg = (
            f"गूगल वाक् पहचान सेवा से संपर्क नहीं हो सका: {e}"
            if lang == "hi"
            else f"Could not request results from Google Speech Recognition service: {e}"
        )
        return "", msg
    except Exception as e:
        return "", f"Speech processing error: {str(e)}"


def build_spoken_summary(risk_level: str, findings: List[Dict[str, Any]], lang: str = "en") -> str:
    """Generate a concise, natural risk summary for TTS reading aloud."""
    count = len(findings)
    if not findings:
        if lang == "hi":
            return "प्राइवेसी चौकीदार रिपोर्ट: कोई संवेदनशील डेटा नहीं मिला। यह प्रॉम्प्ट भेजना पूरी तरह सुरक्षित है।"
        return "Privacy Chowkidar report: No sensitive data detected. This prompt is safe to send."

    types = list({f["type"] for f in findings})
    types_str = ", ".join(types[:3])

    if lang == "hi":
        return (
            f"प्राइवेसी चेतावनी। समग्र जोखिम {risk_level} है। "
            f"कुल {count} संवेदनशील विवरण पाए गए, जिनमें {types_str} शामिल हैं। "
            f"कृपया बाहरी एआई को भेजने से पहले ऑटो-रीडैक्ट विकल्प चुनें।"
        )
    return (
        f"Privacy Alert. Overall risk level is {risk_level}. "
        f"Found {count} sensitive items including {types_str}. "
        f"We recommend auto-redacting before submitting to external AI."
    )


def text_to_speech(text: str, lang: str = "en") -> Tuple[bytes | None, str | None]:
    """Convert text to spoken MP3 audio bytes using gTTS."""
    if not text:
        return None, "Empty text provided for TTS."

    try:
        from gtts import gTTS
    except ImportError:
        return None, "Library 'gTTS' is not installed. Please run: pip install gTTS"

    try:
        gtts_lang = "hi" if lang == "hi" else "en"
        tts = gTTS(text=text, lang=gtts_lang, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.getvalue(), None
    except Exception as e:
        return None, f"TTS generation error: {str(e)}"
