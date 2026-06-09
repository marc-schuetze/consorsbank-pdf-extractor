"""
Consorsbank PDF Extractor Package

Extract transaction data from Consorsbank PDF statements and convert to CSV format.

Text extraction uses poppler's ``pdftotext -layout`` (system binary), which
preserves the column layout and word spacing of the original statement. This is
essential because Consorsbank changed its PDF layout over the years: older
statements (<= ~2024) keep spaces between fields, while newer ones (2025+) run
dates and numbers together. ``pdftotext -layout`` normalises both into the same
aligned, space-separated text so a single parser can handle every era.
"""

import logging
import shutil
import subprocess


class PdftotextNotFound(RuntimeError):
    """Raised when the poppler ``pdftotext`` binary is not available."""


def _ensure_pdftotext():
    if shutil.which("pdftotext") is None:
        raise PdftotextNotFound(
            "The 'pdftotext' binary (poppler-utils) is required but was not found. "
            "Install it with: apt install poppler-utils  (Debian/Ubuntu) "
            "or: brew install poppler  (macOS)."
        )


def extract_pdf_to_text(pdf_file_path):
    """
    Extract text content from a PDF file using ``pdftotext -layout``.

    Args:
        pdf_file_path (str): Path to the PDF file

    Returns:
        str: Extracted text content, or None if extraction fails

    Raises:
        PdftotextNotFound: If the pdftotext binary is unavailable.
    """
    _ensure_pdftotext()
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", pdf_file_path, "-"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        logging.error(f"PDF file not found: {pdf_file_path}")
        return None
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", "replace").strip()
        logging.error(f"pdftotext failed on {pdf_file_path}: {stderr}")
        return None

    text = result.stdout.decode("utf-8", "replace")
    if not text.strip():
        logging.error(f"No text content extracted from {pdf_file_path}")
        return None

    logging.debug(f"Extracted {len(text)} characters from {pdf_file_path}")
    return text
