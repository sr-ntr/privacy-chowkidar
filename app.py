"""app.py - Privacy Chowkidar (Streamlit Application).

In-memory privacy pre-flight scanner for prompts, files, and images before sending to LLMs.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from detectors import scan_text, redact, calculate_risk_level
from extractors import extract_uploaded_file, extract_from_text

# Configure page
st.set_page_config(
    page_title="Privacy Chowkidar (प्राइवेसी चौकीदार)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# LLM Target definitions
LLM_SERVICES = {
    "ChatGPT (OpenAI)": {
        "url": "https://chatgpt.com",
        "guidance": "Prompts may be stored or reviewed for model improvement unless opt-out or enterprise controls are configured. Check the vendor's current policy.",
    },
    "Claude (Anthropic)": {
        "url": "https://claude.ai",
        "guidance": "Data handling depends on your plan (Free/Pro vs. API/Commercial). Check the vendor's current policy.",
    },
    "Gemini (Google)": {
        "url": "https://gemini.google.com",
        "guidance": "Conversations may be retained and sampled by human reviewers unless Workspace protections apply. Check the vendor's current policy.",
    },
    "Microsoft Copilot": {
        "url": "https://copilot.microsoft.com",
        "guidance": "Commercial data protection applies to certain enterprise logins, while consumer accounts differ. Check the vendor's current policy.",
    },
    "DeepSeek": {
        "url": "https://chat.deepseek.com",
        "guidance": "Cloud-hosted chat services process user submissions according to their server region and terms. Check the vendor's current policy.",
    },
    "Perplexity": {
        "url": "https://www.perplexity.ai",
        "guidance": "Queries may be indexed or used to refine retrieval responses. Check the vendor's current policy.",
    },
    "Other LLM / API": {
        "url": "https://openai.com",
        "guidance": "Always assume external LLMs can log or retain inputs unless covered by a signed BAA or Zero Data Retention agreement. Check the vendor's current policy.",
    },
}

# Sidebar LLM selector
with st.sidebar:
    st.title("🛡️ Privacy Chowkidar")
    st.caption("Privacy pre-flight watchman for your AI prompts")
    st.divider()

    st.subheader("Target LLM Destination")
    selected_llm = st.selectbox("Where will you send this prompt?", list(LLM_SERVICES.keys()))
    llm_info = LLM_SERVICES[selected_llm]
    st.info(f"**Policy Note:** {llm_info['guidance']}")
    st.link_button(f"Open {selected_llm} ↗", llm_info["url"])

    st.divider()
    st.markdown(
        """
        **Zero-Data Guarantee**:
        All scanning runs exclusively in ephemeral memory.
        No database, no disk logging, and no prompt tracking.
        """
    )

st.title("🛡️ Privacy Chowkidar (प्राइवेसी चौकीदार)")
st.markdown(
    "Scan your prompts, documents, or screenshots for sensitive Indian and global PII, "
    "financial data, and secret keys **before** sending them to any AI model."
)

# Tabs for input mode
tab_prompt, tab_file = st.tabs(["✍️ Text Prompt", "📁 Document / Image Upload"])

raw_content = ""
warning_msg = None

with tab_prompt:
    prompt_input = st.text_area(
        "Enter your prompt text to scan:",
        height=180,
        placeholder="Type or paste text here (e.g., 'Review this account for Aadhaar 5489 1234 5678 and PAN ABCDE1234F')...",
        key="text_prompt_input",
    )
    if prompt_input:
        raw_content, warning_msg = extract_from_text(prompt_input)

with tab_file:
    uploaded_file = st.file_uploader(
        "Upload a document or screenshot to inspect:",
        type=["txt", "csv", "pdf", "docx", "png", "jpg", "jpeg", "webp"],
        key="file_upload_input",
    )
    if uploaded_file:
        file_text, file_warn = extract_uploaded_file(uploaded_file)
        if file_warn:
            st.warning(file_warn)
        if file_text:
            raw_content = file_text
            st.text_area("Extracted file content:", value=raw_content, height=140, disabled=True)

# Main scan and analysis
if raw_content:
    findings = scan_text(raw_content)
    risk_level, risk_color, risk_title = calculate_risk_level(findings)

    # Risk Meter Header
    st.markdown(f"### Overall Risk Assessment: <span style='color:{risk_color}; font-weight:bold;'>{risk_title} ({risk_level})</span>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    col1.metric("Critical Secrets", sev_counts["Critical"])
    col2.metric("High PII (Aadhaar/PAN/Phone)", sev_counts["High"])
    col3.metric("Medium Identifiers", sev_counts["Medium"])
    col4.metric("Context Flags", sev_counts["Low"])

    if findings:
        st.subheader("⚠️ Detected Sensitive Items")
        # Prepare findings table
        table_rows = []
        for i, f in enumerate(findings, 1):
            table_rows.append({
                "#": i,
                "Type": f["type"],
                "Severity": f["severity"],
                "Masked Preview": f["masked"],
                "Threat Explanation": f["threat_en"],
                "Recommended Action": f["action_en"],
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

        st.divider()
        st.subheader("Take Action")
        action_choice = st.radio(
            "Choose how you want to proceed:",
            [
                "Auto-redact and continue (Recommended)",
                "Edit prompt manually",
                "Send anyway (I understand the risk)",
            ],
            index=0,
        )

        redacted_content = redact(raw_content, findings)

        if action_choice == "Auto-redact and continue (Recommended)":
            st.success("✅ Sensitive tokens replaced with safe placeholder tags:")
            st.code(redacted_content, language="text")
        elif action_choice == "Edit prompt manually":
            st.info("Edit your content below to remove sensitive segments:")
            edited_text = st.text_area("Edit prompt:", value=raw_content, height=160)
            if edited_text != raw_content:
                st.write("Preview of edited prompt:")
                st.code(edited_text, language="text")
        else:
            st.error("⚠️ Proceeding with unredacted sensitive data. Check your target LLM's privacy agreement!")
            st.code(raw_content, language="text")

    else:
        st.success("🎉 No sensitive PII, credentials, or dangerous patterns detected. Clean to send!")
        st.code(raw_content, language="text")
else:
    st.info("Enter text in the box above or upload a document/image to perform pre-flight scanning.")
