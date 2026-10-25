"""app.py - Privacy Chowkidar (Streamlit Application).

In-memory privacy pre-flight scanner for prompts, files, and images before sending to LLMs.
Bilingual support in English and Hindi, with voice assistant (STT + TTS).

Sarvam AI powers all voice and LLM features:
  - Speech-to-Text: Sarvam Saaras (saaras:v2)
  - Text-to-Speech: Sarvam Bulbul (bulbul:v2)
  - Risk summaries: sarvam-105b-conversations
"""

from __future__ import annotations
import os
from pathlib import Path

import streamlit as st
import pandas as pd

# Load .env so SARVAM_API_KEY is available to voice.py at runtime
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass  # python-dotenv optional; key may already be in environment
from detectors import scan_text, redact, calculate_risk_level
from extractors import extract_uploaded_file, extract_from_text
from i18n import t
from voice import transcribe_audio, text_to_speech, build_spoken_summary

# Configure page
st.set_page_config(
    page_title="Privacy Chowkidar (प्राइवेसी चौकीदार)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for prompt text
if "prompt_text" not in st.session_state:
    st.session_state["prompt_text"] = ""

# Sidebar Language Selection
lang_selection = st.sidebar.radio(
    "🌐 Language / भाषा",
    options=["English", "हिन्दी"],
    index=0,
    horizontal=True,
)
lang_code = "hi" if lang_selection == "हिन्दी" else "en"

# LLM Target definitions
LLM_SERVICES = {
    "ChatGPT (OpenAI)": {
        "url": "https://chatgpt.com",
        "guidance": "Prompts may be stored or reviewed for model improvement unless opt-out or enterprise controls are configured. Check the vendor's current policy.",
        "guidance_hi": "प्रॉम्प्ट मॉडल सुधार के लिए संग्रहीत या समीक्षित किए जा सकते हैं जब तक कि ऑप्ट-आउट न किया गया हो। विक्रेता की वर्तमान नीति जांचें।",
    },
    "Claude (Anthropic)": {
        "url": "https://claude.ai",
        "guidance": "Data handling depends on your plan (Free/Pro vs. API/Commercial). Check the vendor's current policy.",
        "guidance_hi": "डेटा हैंडलिंग आपकी योजना (फ्री/प्रो बनाम एपीआई) पर निर्भर करती है। विक्रेता की वर्तमान नीति जांचें।",
    },
    "Gemini (Google)": {
        "url": "https://gemini.google.com",
        "guidance": "Conversations may be retained and sampled by human reviewers unless Workspace protections apply. Check the vendor's current policy.",
        "guidance_hi": "बातचीत मानवीय समीक्षकों द्वारा जांची जा सकती है जब तक कि वर्कस्पेस सुरक्षा लागू न हो। विक्रेता की वर्तमान नीति जांचें।",
    },
    "Microsoft Copilot": {
        "url": "https://copilot.microsoft.com",
        "guidance": "Commercial data protection applies to certain enterprise logins, while consumer accounts differ. Check the vendor's current policy.",
        "guidance_hi": "व्यावसायिक डेटा सुरक्षा एंटरप्राइज़ लॉगिन पर लागू होती है, उपभोक्ता खातों की शर्तें भिन्न हैं। विक्रेता की वर्तमान नीति जांचें।",
    },
    "DeepSeek": {
        "url": "https://chat.deepseek.com",
        "guidance": "Cloud-hosted chat services process user submissions according to their server region and terms. Check the vendor's current policy.",
        "guidance_hi": "क्लाउड चैट सेवाएँ अपने सर्वर क्षेत्र और शर्तों के अनुसार डेटा संसाधित करती हैं। विक्रेता की वर्तमान नीति जांचें।",
    },
    "Perplexity": {
        "url": "https://www.perplexity.ai",
        "guidance": "Queries may be indexed or used to refine retrieval responses. Check the vendor's current policy.",
        "guidance_hi": "प्रश्नों को खोज प्रतिक्रियाओं को परिष्कृत करने के लिए अनुक्रमित किया जा सकता है। विक्रेता की वर्तमान नीति जांचें।",
    },
    "Other LLM / API": {
        "url": "https://openai.com",
        "guidance": "Always assume external LLMs can log or retain inputs unless covered by a signed BAA or Zero Data Retention agreement. Check the vendor's current policy.",
        "guidance_hi": "मान लें कि बाहरी एआई डेटा संग्रहीत कर सकता है जब तक कि शून्य डेटा अनुबंध न हो। विक्रेता की वर्तमान नीति जांचें।",
    },
}

# Sidebar destination details
with st.sidebar:
    st.title(t("app_title", lang_code))
    st.caption(t("app_subtitle", lang_code))
    st.divider()

    st.subheader(t("sidebar_dest_title", lang_code))
    selected_llm = st.selectbox(t("sidebar_select_llm", lang_code), list(LLM_SERVICES.keys()))
    llm_info = LLM_SERVICES[selected_llm]
    guidance_text = llm_info["guidance_hi"] if lang_code == "hi" else llm_info["guidance"]
    st.info(f"**{t('sidebar_policy_note', lang_code)}** {guidance_text}")
    st.link_button(f"{t('sidebar_open_btn', lang_code)} {selected_llm} ↗", llm_info["url"])

    st.divider()
    st.markdown(t("sidebar_zero_guarantee", lang_code))

# Main App Header
st.title(t("app_title", lang_code))
st.markdown(t("tagline", lang_code))

# Tabs for input mode: Text Prompt, File Upload, Voice Prompt
tab_prompt, tab_file, tab_voice = st.tabs([
    t("tab_prompt", lang_code),
    t("tab_file", lang_code),
    t("tab_voice", lang_code),
])

raw_content = ""
warning_msg = None

with tab_voice:
    st.subheader(t("voice_header", lang_code))
    st.caption(t("voice_privacy_warning", lang_code))

    # st.audio_input returns an UploadedFile-like object or bytes
    if hasattr(st, "audio_input"):
        audio_prompt = st.audio_input(t("voice_record_prompt", lang_code), key="voice_input_widget")
        if audio_prompt is not None:
            audio_bytes = audio_prompt.getvalue() if hasattr(audio_prompt, "getvalue") else audio_prompt.read()
            with st.spinner("Transcribing speech... / ऑडियो ट्रांसक्राइब हो रहा है..."):
                transcript, err = transcribe_audio(audio_bytes, lang=lang_code)
                if err:
                    st.warning(err)
                elif transcript:
                    st.success(f"{t('voice_transcribed', lang_code)} **{transcript}**")
                    st.session_state["prompt_text"] = transcript
    else:
        st.info("st.audio_input requires Streamlit 1.35+. Please update Streamlit to enable direct recording.")

with tab_prompt:
    prompt_input = st.text_area(
        t("prompt_label", lang_code),
        value=st.session_state.get("prompt_text", ""),
        height=180,
        placeholder=t("prompt_placeholder", lang_code),
        key="text_prompt_input",
    )
    if prompt_input:
        raw_content, warning_msg = extract_from_text(prompt_input)

with tab_file:
    uploaded_file = st.file_uploader(
        t("upload_label", lang_code),
        type=["txt", "csv", "pdf", "docx", "png", "jpg", "jpeg", "webp"],
        key="file_upload_input",
    )
    if uploaded_file:
        file_text, file_warn = extract_uploaded_file(uploaded_file)
        if file_warn:
            st.warning(file_warn)
        if file_text:
            raw_content = file_text
            st.text_area(t("extracted_file_label", lang_code), value=raw_content, height=140, disabled=True)

# Main scan and analysis
if raw_content:
    findings = scan_text(raw_content)
    risk_level, risk_color, _ = calculate_risk_level(findings)
    risk_localized = t(f"risk_{risk_level.lower()}", lang_code)

    # Risk Meter Header
    st.markdown(
        f"### {t('overall_risk_title', lang_code)}: "
        f"<span style='color:{risk_color}; font-weight:bold;'>{risk_localized} ({risk_level})</span>",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    col1.metric(t("metric_critical", lang_code), sev_counts["Critical"])
    col2.metric(t("metric_high", lang_code), sev_counts["High"])
    col3.metric(t("metric_medium", lang_code), sev_counts["Medium"])
    col4.metric(t("metric_low", lang_code), sev_counts["Low"])

    # Spoken Audio Risk Summary Button
    spoken_summary_text = build_spoken_summary(risk_localized, findings, lang=lang_code)
    tts_col1, tts_col2 = st.columns([1, 2])
    with tts_col1:
        if st.button(t("voice_read_summary", lang_code), key="btn_read_aloud"):
            with st.spinner(t("tts_generating", lang_code)):
                audio_bytes, tts_err = text_to_speech(spoken_summary_text, lang=lang_code)
                if tts_err:
                    st.error(tts_err)
                elif audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

    if findings:
        st.subheader(t("detected_heading", lang_code))
        # Prepare findings table
        table_rows = []
        for i, f in enumerate(findings, 1):
            threat = f["threat_hi"] if lang_code == "hi" else f["threat_en"]
            action = f["action_hi"] if lang_code == "hi" else f["action_en"]
            table_rows.append({
                t("col_num", lang_code): i,
                t("col_type", lang_code): f["type"],
                t("col_severity", lang_code): f["severity"],
                t("col_preview", lang_code): f["masked"],
                t("col_threat", lang_code): threat,
                t("col_action", lang_code): action,
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

        st.divider()
        st.subheader(t("take_action", lang_code))
        action_choice = st.radio(
            t("action_choice_label", lang_code),
            [
                t("act_autoredact", lang_code),
                t("act_edit", lang_code),
                t("act_send_anyway", lang_code),
            ],
            index=0,
        )

        redacted_content = redact(raw_content, findings)

        if action_choice == t("act_autoredact", lang_code):
            st.success(t("redact_success", lang_code))
            st.code(redacted_content, language="text")
        elif action_choice == t("act_edit", lang_code):
            st.info(t("edit_instruction", lang_code))
            edited_text = st.text_area(t("act_edit", lang_code), value=raw_content, height=160)
            if edited_text != raw_content:
                st.write(t("edit_preview", lang_code))
                st.code(edited_text, language="text")
        else:
            st.error(t("send_warn", lang_code))
            st.code(raw_content, language="text")

    else:
        st.success(t("safe_clean", lang_code))
        st.code(raw_content, language="text")
else:
    st.info(t("waiting_input", lang_code))
