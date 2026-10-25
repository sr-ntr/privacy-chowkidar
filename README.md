# Privacy Chowkidar (प्राइवेसी चौकीदार)

"Chowkidar" means watchman. Privacy Chowkidar checks your prompts, documents and screenshots for sensitive information before you send them to an AI tool like ChatGPT, Claude, Gemini, Copilot, DeepSeek or Perplexity. If it finds something, it warns you, explains the risk in plain language, and offers to hide the sensitive parts for you. It works in English and Hindi, and has voice input and spoken warnings.

---

## What it does

1. **Finds sensitive data**
   - Indian IDs: Aadhaar, PAN, mobile numbers, passport numbers
   - Financial details: card numbers, UPI IDs, IFSC codes
   - Secrets: API keys, tokens, private keys, passwords, IP addresses
   - Context words such as "confidential", "salary" or "diagnosis" (low-level warning)
2. **Hides it for you**: replaces sensitive text with tags like `[AADHAAR_REDACTED]`, so the rest of your prompt still makes sense.
3. **Reads your files**: typed text, `.txt`, `.csv`, `.pdf`, `.docx`, and images or screenshots (text is read from the image).
4. **Works in English and Hindi**: the whole screen can be switched between English and हिन्दी.
5. **Voice**: speak your prompt instead of typing, and listen to the risk summary read aloud.
6. **Guidance per AI tool**: pick the tool you plan to use and get a link plus general tips.

Nothing you enter is saved. Everything is handled in memory while the app is open.

---

## Project structure

```text
privacy-chowkidar/
├── app.py                # Main screen and workflow
├── detectors.py          # Detection rules, risk level and redaction
├── extractors.py         # Reads text from files and images
├── voice.py              # Speech-to-text and text-to-speech
├── i18n.py               # English and Hindi text
├── tests/
│   └── test_detectors.py # Unit tests
├── requirements.txt      # Python packages
├── packages.txt          # System packages for Streamlit Cloud
├── pytest.ini            # Test settings
├── LICENSE               # MIT License
└── README.md
```

---

## Run it on your computer

### 1. What you need
- Python 3.10 or 3.11
- A Sarvam AI API key for the voice features (get one from the Sarvam dashboard)
- Optional, for reading text from images: Tesseract
  ```bash
  # Ubuntu / Debian
  sudo apt install tesseract-ocr tesseract-ocr-hin
  # macOS
  brew install tesseract tesseract-lang
  ```
  Without Tesseract the app still works, but image text reading is switched off.

### 2. Install
```bash
cd privacy-chowkidar
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your API key
Create a file at `.streamlit/secrets.toml`:
```toml
SARVAM_API_KEY = "your-key-here"
```
This file must be listed in `.gitignore` so your key is never pushed to GitHub.

### 4. Run the tests
```bash
pytest
```

### 5. Start the app
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## Try it with sample text

Paste this (all fake data) into the prompt box:
```text
Please review my account details:
Name: Rahul Sharma
Aadhaar: 5489 1234 5678
PAN: ABCDE1234F
Phone: +91 9876543210
Card: 4532 0150 0000 0007
Email: rahul.sharma@example.com
```

You should see:
- Overall risk: Critical
- Hidden previews such as `XXXX XXXX 5678` and `AB******4F`
- After clicking auto-redact:
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

## Limitations

- **It can miss things.** Detection uses fixed patterns, so unusual formats, deliberately disguised text or new kinds of keys may not be caught.
- **It can flag too much.** Some ordinary long numbers or random-looking strings may be mistaken for sensitive data.
- **It is not an enterprise security product.** This is a prototype to help individuals think before they share.
- **Voice sends data to Sarvam AI.** Your recorded speech and the text read aloud are processed by Sarvam's servers. Do not speak passwords, ID numbers or other sensitive details.
- **Names and addresses are not detected yet.**

---

## Future work

- A browser extension that checks prompts directly inside ChatGPT, Claude and Gemini.
- Speech that runs fully on your device, so no audio leaves your computer.
- Detection of names, addresses and organisations using language models.
- A proxy that cleans prompts automatically before they reach an AI service.