# 🛡️ Privacy Chowkidar (प्राइवेसी चौकीदार)

> *"Chowkidar" means watchman.* **Privacy Chowkidar** is a lightweight, zero-storage privacy pre-flight layer that sits in front of external LLMs (ChatGPT, Claude, Gemini, Copilot, DeepSeek, Perplexity, etc.). It scans prompts, documents, and screenshots for sensitive Indian and global PII, financial identifiers, and secrets BEFORE they are transmitted, warns users with plain-language threat explanations, and provides auto-redaction and bilingual voice feedback (English / हिन्दी).

---

## 🌟 Key Features

1. **Zero-Storage, Pure In-Memory Architecture**:
   - Everything is processed strictly in RAM. User content is never saved to disk, logged, or retained.
2. **Comprehensive Sensitive Data Detection (`detectors.py`)**:
   - **Indian PII**: Aadhaar (12-digit format with prefix validation), PAN card (`[A-Z]{5}[0-9]{4}[A-Z]`), Indian Mobile numbers (+91 / 0 prefix, starting with 6-9), Passport numbers.
   - **Financial Identifiers**: Credit/Debit card numbers (validated with the **Luhn algorithm** to prevent false positives), UPI IDs (`user@okhdfcbank`, `user@paytm`, etc.), IFSC codes.
   - **Credentials & Infrastructure**: API keys & tokens (`sk-...`, `AKIA...`, `ghp_...`, `AIza...`, JWTs), Private Key blocks, password declarations (`password: ...`), IPv4 addresses.
   - **Context Indicators**: Flags confidentiality and medical indicators (`confidential`, `salary`, `diagnosis`, `NDA`, etc.) as Low severity warnings.
3. **Smart Auto-Redaction**:
   - Replaces sensitive tokens with standardized tags (e.g. `[AADHAAR_REDACTED]`, `[PAN_REDACTED]`, `[CARD_REDACTED]`) while preserving prompt grammar and context.
4. **Multi-Format Extraction (`extractors.py`)**:
   - Direct text prompts.
   - Documents: `.txt`, `.csv`, `.pdf` (`pypdf`), `.docx` (`python-docx`).
   - Images & Screenshots: OCR via `pytesseract` (`eng+hin`) with graceful fallback if the Tesseract binary is absent.
5. **Bilingual Voice Assistant (`voice.py` & `i18n.py`)**:
   - Language toggle: **English** and **हिन्दी** across all UI headers, tables, threats, and actions.
   - Speech-to-Text: `st.audio_input` with `SpeechRecognition` (`recognize_google` with `en-IN` / `hi-IN`). No PyAudio or Microphone required.
   - Text-to-Speech: Spoken risk summaries using `gTTS` (`en` / `hi`), streamed directly through `st.audio`.
6. **Target LLM Guidance**:
   - Interactive dropdown for ChatGPT, Claude, Gemini, Microsoft Copilot, DeepSeek, and Perplexity with direct links and data policy guidance.

---

## 🏗️ Project Structure

```text
privacy-chowkidar/
├── app.py                # Streamlit UI, risk meter, and workflow orchestrator
├── detectors.py          # Regex rules, Luhn validation, risk ranking, and redaction engine
├── extractors.py         # In-memory document and OCR text extraction
├── voice.py              # Bilingual Speech-to-Text and Text-to-Speech helpers
├── i18n.py               # English & Hindi translation dictionaries
├── tests/
│   └── test_detectors.py # Pytest unit test suite (8 tests)
├── requirements.txt      # Pinned Python package dependencies
├── packages.txt          # Linux system dependencies for Streamlit Cloud
├── pytest.ini            # Pytest configuration
├── LICENSE               # MIT License
└── README.md             # Project documentation
```

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- Python 3.10 or 3.11
- (Optional for OCR) Tesseract binary:
  ```bash
  # Debian / Ubuntu
  sudo apt install tesseract-ocr tesseract-ocr-hin
  # macOS
  brew install tesseract tesseract-lang
  ```

### 2. Environment & Dependencies
```bash
# Clone the repository
cd privacy-chowkidar

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python requirements
pip install -r requirements.txt
```

### 3. Run the Unit Tests
```bash
pytest
```
*All 8 unit tests in `tests/test_detectors.py` will run and pass.*

### 4. Launch the Streamlit App
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deployment on Streamlit Community Cloud

This project is fully ready for zero-configuration deployment to [Streamlit Community Cloud](https://streamlit.io/cloud):
1. Push your repository to GitHub.
2. In Streamlit Cloud, create a **New App** and select your repository and `main` branch.
3. Set the main file path to `app.py`.
4. Streamlit Community Cloud will automatically detect:
   - `requirements.txt` for Python packages.
   - `packages.txt` for Linux packages (`tesseract-ocr`, `tesseract-ocr-hin`).
5. Click **Deploy**!

---

## 🧪 Testing with Sample Input

Try entering this prompt into the text area:
```text
Please review my account details:
Name: Rahul Sharma
Aadhaar: 5489 1234 5678
PAN: ABCDE1234F
Phone: +91 9876543210
Card: 4532 0150 0000 0007
Email: rahul.sharma@example.com
```

### Expected Output:
- **Overall Risk**: `Critical Risk / गंभीर जोखिम (Critical)`
- **Metrics**: 1 Critical Secret (Luhn-verified card), 3 High PII (Aadhaar, PAN, Phone), 1 Medium Identifier (Email).
- **Masked Previews**: `XXXX XXXX 5678`, `AB******4F`, `+91 XXXXX 3210`, `XXXX-XXXX-XXXX-0007`, `ra***@example.com`.
- **Auto-Redaction**:
  ```text
  Please review my account details:
  Name: Rahul Sharma
  Aadhaar: [AADHAAR_REDACTED]
  PAN: [PAN_REDACTED]
  Phone: [PHONE_REDACTED]
  Card: [CARD_REDACTED]
  Email: [EMAIL_REDACTED]
  ```

---

## ⚠️ Limitations

- **Pattern & Heuristic Boundaries**: Detection relies on deterministic regular expressions and mathematical checks (such as Luhn). Obfuscated text (e.g. *f-o-u-r-5-three*), zero-width characters, or novel token formats may not be caught.
- **Over-flagging**: High-entropy strings, hash digests, or generic 10/12-digit numbers can occasionally match PII patterns.
- **Not an Enterprise DLP Substitute**: Privacy Chowkidar is a user-side pre-flight prototype intended to raise user awareness. It is not an enterprise-grade Data Loss Prevention (DLP) or compliance audit appliance.
- **Third-Party Voice Processing**: Voice STT and TTS connect to external Google Speech services. Users are explicitly warned not to speak sensitive credentials aloud.

---

## 🔮 Future Work

- **Browser Extension**: An inline extension that intercepts prompt submissions directly inside ChatGPT, Claude, and Gemini web interfaces.
- **Offline & On-Device Speech**: Replace Google Web Speech with lightweight on-device models (e.g. Whisper.cpp, Vosk, or Sherpa-ONNX) for complete offline voice privacy.
- **NER-Based Detection**: Integrate compact Named Entity Recognition models (Indic-BERT, spaCy, GLiNER) to detect names, addresses, and organizations without fixed regex patterns.
- **Direct API Reverse Proxy**: A drop-in OpenAI-compatible proxy server (`/v1/chat/completions`) that transparently redacts prompts on the wire before proxying to upstream LLMs.

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
