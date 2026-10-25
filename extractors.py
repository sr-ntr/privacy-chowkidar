"""extractors.py - In-memory text extraction for Privacy Chowkidar.

Extracts text from:
- Plain text & CSV (.txt, .csv)
- PDF documents (.pdf via pypdf)
- Word documents (.docx via python-docx)
- Images (.png, .jpg, .jpeg, .webp, .tiff via pytesseract OCR)

All processing is performed strictly in-memory without persisting files to disk.
"""

from __future__ import annotations
import io
import os
import shutil
from typing import Any, Tuple


def extract_from_text(text: str) -> Tuple[str, str | None]:
    """Extract clean text from string prompt."""
    if not text:
        return "", None
    return text.strip(), None


def extract_from_txt_or_csv(file_bytes: bytes) -> Tuple[str, str | None]:
    """Decode text from plain text or CSV bytes."""
    try:
        return file_bytes.decode("utf-8").strip(), None
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1").strip(), None
        except Exception as e:
            return "", f"Error reading text file: {str(e)}"


def extract_from_pdf(file_bytes: bytes) -> Tuple[str, str | None]:
    """Extract text from PDF bytes using pypdf."""
    try:
        import pypdf
    except ImportError:
        return "", "Library 'pypdf' is not installed. Please run: pip install pypdf"

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(text)
        combined = "\n\n".join(pages_text).strip()
        if not combined:
            return "", "PDF contains no extractable text (it might be a scanned image)."
        return combined, None
    except Exception as e:
        return "", f"Error parsing PDF: {str(e)}"


def extract_from_docx(file_bytes: bytes) -> Tuple[str, str | None]:
    """Extract text from Word .docx bytes using python-docx."""
    try:
        import docx
    except ImportError:
        return "", "Library 'python-docx' is not installed. Please run: pip install python-docx"

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        return "\n".join(paragraphs).strip(), None
    except Exception as e:
        return "", f"Error parsing DOCX: {str(e)}"


def extract_from_image(file_bytes: bytes) -> Tuple[str, str | None]:
    """Extract text from image bytes using pytesseract OCR (eng + hin).

    If the Tesseract binary is missing, displays a friendly warning and continues without crashing.
    """
    try:
        from PIL import Image
    except ImportError:
        return "", "Library 'Pillow' is not installed. Please run: pip install Pillow"

    try:
        import pytesseract
    except ImportError:
        return "", "Library 'pytesseract' is not installed. Please run: pip install pytesseract"

    # Check if tesseract binary is accessible
    tesseract_cmd = shutil.which("tesseract") or getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    is_installed = bool(shutil.which(tesseract_cmd) if os.path.isabs(tesseract_cmd) else shutil.which("tesseract"))

    if not is_installed:
        return (
            "",
            "ℹ️ Tesseract OCR is not installed on this system. "
            "To enable image text extraction, install it via: "
            "`sudo apt install tesseract-ocr tesseract-ocr-hin` (or deploy with packages.txt on Streamlit Cloud).",
        )

    try:
        image = Image.open(io.BytesIO(file_bytes))
        try:
            text = pytesseract.image_to_string(image, lang="eng+hin")
        except Exception:
            # Fallback to English if Hindi model is not installed locally
            text = pytesseract.image_to_string(image, lang="eng")

        if not text.strip():
            return "", "No readable text detected in the uploaded image."
        return text.strip(), None
    except Exception as e:
        return "", f"Error processing image with OCR: {str(e)}"


def extract_uploaded_file(file_obj: Any) -> Tuple[str, str | None]:
    """Route uploaded file object (Streamlit UploadedFile or file-like) to the right extractor.

    Returns:
        (extracted_text, warning_or_error)
    """
    if file_obj is None:
        return "", None

    # Get file name and bytes
    filename = getattr(file_obj, "name", "")
    ext = os.path.splitext(filename)[1].lower()

    if hasattr(file_obj, "getvalue"):
        file_bytes = file_obj.getvalue()
    elif hasattr(file_obj, "read"):
        file_bytes = file_obj.read()
    elif isinstance(file_obj, bytes):
        file_bytes = file_obj
    else:
        return "", "Unsupported file input format."

    if ext in (".txt", ".csv"):
        return extract_from_txt_or_csv(file_bytes)
    elif ext == ".pdf":
        return extract_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return extract_from_docx(file_bytes)
    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
        return extract_from_image(file_bytes)
    else:
        return "", f"Unsupported file type '{ext}'. Supported: .txt, .csv, .pdf, .docx, .png, .jpg"
