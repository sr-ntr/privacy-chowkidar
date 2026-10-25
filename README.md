# Privacy Chowkidar (प्राइवेसी चौकीदार)

A privacy pre-flight layer that sits in front of LLMs (ChatGPT, Claude, Gemini, etc.). It scans prompts, documents, and images for sensitive data BEFORE transmission, alerts the user to specific threats, and supports bilingual voice feedback (English / हिन्दी).

## Overview
- **Zero-Storage Architecture**: All processing happens strictly in-memory.
- **Pre-flight Sensitive Data Detection**: Scans Indian and global PII, financial identifiers, credentials, and context flags.
- **Redaction Engine**: Safe auto-masking before sharing with LLMs.
- **Bilingual Interface & Voice**: English & Hindi voice assistance.

## Quick Start
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
