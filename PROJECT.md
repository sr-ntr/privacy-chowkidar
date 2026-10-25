# Task: Build "Privacy Chowkidar" — a working Streamlit prototype

"Chowkidar" means watchman. This is a privacy pre-flight layer that sits in front of any
popular LLM (ChatGPT, Claude, Gemini, etc.). It scans prompts, documents, and images for
sensitive data BEFORE the user sends them, warns them, and explains the specific threats.
It has a voice assistant in English and Hindi.

## Constraints
- Python 3.11, Streamlit only. Use already specified API, no database.
- Must run locally and on Streamlit Community Cloud.
- Keep it simple: at most 6 source files. Prefer readability over cleverness.
- Everything is processed in memory. Never store, log, or transmit user content
  (except the speech/TTS calls described below).
- This is a prototype. Prioritise a working end-to-end flow over completeness.

## Features

### 1. Detector (detectors.py)
Regex + simple validation. Each finding has: type, severity (Low/Medium/High/Critical),
masked preview (e.g. XXXX XXXX 1234), threat explanation in English and Hindi, and a
recommended action. Detect:
- Aadhaar (12 digits, optional spaces), PAN, Indian mobile numbers, email
- Credit/debit card numbers (validate with Luhn), UPI IDs, IFSC codes, passport numbers
- API keys/tokens (sk-..., AKIA..., ghp_..., AIza..., JWT), private key blocks,
  "password:" style patterns, IP addresses
- Context keywords (confidential, salary, diagnosis, medical, bank statement, etc.)
  as Low severity "context" flags
Also provide a redact() function that replaces findings with tags like [AADHAAR_REDACTED].

### 2. Inputs (extractors.py)
- Text prompt box
- File upload: .txt, .csv, .pdf (pypdf), .docx (python-docx)
- Image upload: OCR with pytesseract (lang eng+hin). If the Tesseract binary is missing,
  show a friendly warning and continue without crashing.

### 3. Warning UI (app.py)
- Overall risk meter: Low / Medium / High / Critical (based on highest severity + count)
- Findings table with masked previews, plain-language threats (identity theft, SIM-swap,
  phishing, financial fraud, account takeover, credential leakage, data retention by
  third parties), and what to do instead
- Actions: "Auto-redact and continue", "Edit prompt", "Send anyway (I understand the risk)"
- Show the sanitised text in a copyable box
- Sidebar dropdown for the target LLM (ChatGPT, Claude, Gemini, Copilot, DeepSeek,
  Perplexity, Other). It shows generic guidance plus a link to open that tool. Do NOT make
  specific claims about any vendor's data policy; say "check the vendor's current policy".

### 4. Bilingual voice assistant (voice.py)
- Language toggle: English / हिन्दी, applied to the whole UI via a small i18n dict
- Speech-to-text: st.audio_input -> SpeechRecognition recognize_google using the WAV bytes
  (language codes en-IN / hi-IN). Do NOT use PyAudio or the Microphone class.
- The transcript goes into the prompt box and is scanned automatically
- Text-to-speech: gTTS (lang "en" / "hi") reads the risk summary aloud; play with st.audio
- Handle failures (no speech, network error) with clear messages
- Show a visible note that voice features send audio/text to Google services, so users
  should not speak sensitive data

## Project structure
privacy-chowkidar/
  app.py, detectors.py, extractors.py, voice.py, i18n.py,
  tests/test_detectors.py, requirements.txt, packages.txt, README.md, .gitignore, LICENSE

- requirements.txt: streamlit, pypdf, python-docx, pytesseract, Pillow, SpeechRecognition,
  gTTS, pandas, pytest (pin versions that work)
- packages.txt (for Streamlit Cloud): tesseract-ocr, tesseract-ocr-hin
- Write 6-8 pytest tests for the detectors (valid and invalid Aadhaar/PAN/card, redaction)

## Version control (mandatory)
Run `git init` first. Add a Python .gitignore. Make a commit at the end of EACH stage using
Conventional Commit messages:
1. chore: initialise repo, .gitignore, README skeleton, requirements
2. feat: sensitive-data detectors with redaction
3. test: unit tests for detectors
4. feat: text, document and image extraction
5. feat: streamlit UI with risk meter and warnings
6. feat: bilingual i18n (English/Hindi)
7. feat: voice input and spoken warnings
8. docs: README with setup, usage, limitations, deployment
Do NOT add a remote or push. I will push to GitHub myself.

## Definition of done
- `streamlit run app.py` works on a fresh venv after `pip install -r requirements.txt`
- `pytest` passes
- A sample prompt containing a fake Aadhaar, PAN and phone number produces a High/Critical
  warning, correct masking and a redacted output
- Hindi UI and Hindi voice input/output work
- README includes a "Limitations" section (regex detection can miss or over-flag; not a
  substitute for a DLP product) and a "Future work" section (browser extension, offline
  speech models, NER-based detection, direct API proxy)
- Print a short summary of the commits and any known issues at the end