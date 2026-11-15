"""
CampusQuery Document Management & Text Extraction Service (Phase 7).

Core Responsibilities:
1. Strict Validation:
   - Accept PDF and DOCX only.
   - Header magic-byte inspection (b"%PDF-", b"PK\x03\x04").
   - Maximum size boundary validation (configurable up to MAX_CONTENT_LENGTH).
   - Filename sanitization and random storage key generation (doc_<uuid>.<ext>).
2. Text Extraction & Honest Diagnostics:
   - PyPDF text extraction across all pages.
   - Python-docx text extraction across paragraphs and tables.
   - Honest status categorization:
     - 'success': Text extracted and queryable.
     - 'scanned_ocr_required': Pages/images exist but zero selectable text (No OCR engine installed).
     - 'encrypted': Password-protected document.
     - 'empty': Zero pages or zero text paragraphs.
     - 'failed': Corrupt or malformed archive/PDF.
3. Storage & Integrity:
   - Files stored strictly in configured DOCUMENTS_UPLOAD_FOLDER outside public static web roots.
   - SHA-256 hash calculated for every file.
   - Transactional consistency: file removed from disk if database commit fails.
4. Protection & Authorization:
   - Download permission enforcement: admins can download any file; students can only download
     files associated with at least one currently published notice.
"""
import io
import os
import uuid
import hashlib
import zipfile
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask import current_app

import pypdf
import pypdf.errors
import docx

from app.database import db
from app.models.document import Document, ALLOWED_DOCUMENT_LABELS
from app.models.notice import Notice
from app.models.notice_document import NoticeDocument

logger = logging.getLogger("campusquery.documents")

ALLOWED_EXTENSIONS = {"pdf", "docx"}
MIME_PDF = "application/pdf"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# 10 MB per-file upload boundary (within 16 MB MAX_CONTENT_LENGTH limit)
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024


# ==============================================================================
# 1. FILE VALIDATION & SECURITY CHECKS
# ==============================================================================
def get_file_extension(filename: str) -> str:
    """Returns lowercase file extension without dot."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].strip().lower()


def validate_uploaded_file(file_storage: FileStorage, max_size: int = MAX_DOCUMENT_SIZE_BYTES) -> Tuple[bool, str, str, bytes]:
    """
    Validates uploaded file:
    - Presence and non-empty filename
    - Allowed extension (.pdf, .docx only)
    - File size within limit
    - Magic signature bytes to prevent renamed executables or corrupt files
    Returns: (is_valid, error_message, detected_mime, file_bytes)
    """
    if not file_storage or not file_storage.filename or not file_storage.filename.strip():
        return False, "No file was selected for upload.", "", b""

    original_name = file_storage.filename.strip()
    ext = get_file_extension(original_name)

    if ext not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"Unsupported file format '.{ext}'. Only official PDF (.pdf) and Word (.docx) documents are permitted.",
            "",
            b""
        )

    # Read bytes safely in memory
    try:
        file_bytes = file_storage.read()
        file_storage.seek(0)
    except Exception as e:
        return False, f"Failed to read uploaded file: {e}", "", b""

    size = len(file_bytes)
    if size == 0:
        return False, "Uploaded file is empty (0 bytes).", "", b""

    if size > max_size:
        limit_mb = round(max_size / (1024 * 1024), 1)
        actual_mb = round(size / (1024 * 1024), 2)
        return (
            False,
            f"File size ({actual_mb} MB) exceeds maximum permitted limit of {limit_mb} MB.",
            "",
            b""
        )

    # Deep signature validation
    if ext == "pdf":
        # PDF files must start with %PDF- (within first 1024 bytes)
        header_sample = file_bytes[:1024]
        if b"%PDF-" not in header_sample:
            return (
                False,
                "Invalid PDF document: file header signature does not match PDF format.",
                "",
                b""
            )
        detected_mime = MIME_PDF

    elif ext == "docx":
        # DOCX files are zip containers starting with PK\x03\x04 and containing document.xml
        if not file_bytes.startswith(b"PK\x03\x04"):
            return (
                False,
                "Invalid Word document: file header signature does not match OpenXML format.",
                "",
                b""
            )
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
                names = zf.namelist()
                if not any("word/document.xml" in n or "[Content_Types].xml" in n for n in names):
                    return (
                        False,
                        "Invalid DOCX structure: missing expected OpenXML document contents.",
                        "",
                        b""
                    )
        except Exception:
            return (
                False,
                "Invalid DOCX document: file is corrupt or not a valid Word archive.",
                "",
                b""
            )
        detected_mime = MIME_DOCX

    else:
        return False, f"Unsupported extension: {ext}", "", b""

    return True, "", detected_mime, file_bytes


# ==============================================================================
# 2. TEXT EXTRACTION & DIAGNOSTICS (PYPDF & PYTHON-DOCX)
# ==============================================================================
def extract_text_from_pdf_bytes(file_bytes: bytes) -> Tuple[str, str, str]:
    """
    Extracts selectable text from PDF bytes using PyPDF.
    Categorizes extraction honestly:
    - 'success': Text found and extracted.
    - 'scanned_ocr_required': Document contains pages but no selectable text stream (OCR not configured).
    - 'encrypted': PDF is password-protected.
    - 'empty': Zero pages.
    - 'failed': Malformed or corrupt structure.
    Returns: (extracted_text, extraction_status, diagnostic_notes)
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))

        # 1. Check encryption
        if reader.is_encrypted:
            return (
                "",
                "encrypted",
                "Encrypted PDF: Password protection prevents text extraction."
            )

        num_pages = len(reader.pages)
        if num_pages == 0:
            return (
                "",
                "empty",
                "Empty PDF: Document contains 0 pages."
            )

        # 2. Extract text page by page
        text_parts = []
        for idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text.strip())
            except Exception as e:
                logger.warning("Error reading page %d: %s", idx + 1, e)

        full_text = "\n\n".join(text_parts).strip()

        # 3. Honest evaluation for scanned documents (Requirement 9)
        if not full_text:
            return (
                "",
                "scanned_ocr_required",
                f"Scanned / image-only PDF ({num_pages} page(s)). No selectable text found. (OCR not implemented)."
            )

        return (
            full_text,
            "success",
            f"Successfully extracted {len(full_text)} characters across {num_pages} page(s)."
        )

    except pypdf.errors.PdfReadError as e:
        return "", "failed", f"PDF structure error: {e}"
    except Exception as e:
        return "", "failed", f"Unexpected PDF parsing error: {e}"


def extract_text_from_docx_bytes(file_bytes: bytes) -> Tuple[str, str, str]:
    """
    Extracts text paragraphs and tables from DOCX bytes using python-docx.
    Categorizes extraction:
    - 'success': Text found and extracted.
    - 'empty': No text paragraphs or table cells.
    - 'failed': Corrupt document archive.
    Returns: (extracted_text, extraction_status, diagnostic_notes)
    """
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        parts = []

        # Extract paragraphs
        for p in doc.paragraphs:
            t = p.text.strip()
            if t:
                parts.append(t)

        # Extract table cells
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)

        full_text = "\n\n".join(parts).strip()

        if not full_text:
            return (
                "",
                "empty",
                "Empty Word Document: No text paragraphs or table contents found."
            )

        return (
            full_text,
            "success",
            f"Successfully extracted {len(full_text)} characters from Word document."
        )

    except Exception as e:
        return "", "failed", f"Failed to parse DOCX document: {e}"


def extract_document_text(file_bytes: bytes, file_type: str) -> Tuple[str, str, str]:
    """Delegates to appropriate extractor based on detected MIME type."""
    if file_type == MIME_PDF or "pdf" in file_type.lower():
        return extract_text_from_pdf_bytes(file_bytes)
    elif file_type == MIME_DOCX or "word" in file_type.lower() or "officedocument" in file_type.lower():
        return extract_text_from_docx_bytes(file_bytes)
    return "", "failed", "Unsupported document extractor type."


# ==============================================================================
# 3. ATOMIC STORAGE & DATABASE PERSISTENCE
# ==============================================================================
def save_uploaded_document(
    file_bytes: bytes,
    original_filename: str,
    file_type: str,
    uploader_id: int,
    label: str = "Supporting Document",
    description: Optional[str] = None,
    notice_id: Optional[int] = None,
    display_label: Optional[str] = None
) -> Tuple[bool, Optional[Document], str]:
    """
    Atomically persists document to disk and records metadata in MySQL.
    - Generates randomized storage filename (doc_<uuid>.<ext>) outside public static paths.
    - Calculates SHA-256 hash.
    - Executes text extraction.
    - Transactional rollback: if DB commit fails, physical file is removed from disk.
    Returns: (success, document_or_none, message)
    """
    ext = get_file_extension(original_filename)
    if ext not in ALLOWED_EXTENSIONS:
        return False, None, f"Unsupported file extension: .{ext}"

    # Generate secure random storage filename (Phase 7 Requirement 4)
    storage_filename = f"doc_{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config.get("DOCUMENTS_UPLOAD_FOLDER")
    if not upload_dir:
        upload_dir = os.path.join(current_app.root_path, "..", "uploads", "documents")

    os.makedirs(upload_dir, exist_ok=True)
    abs_file_path = os.path.abspath(os.path.join(upload_dir, storage_filename))
    rel_file_path = os.path.join("uploads", "documents", storage_filename).replace("\\", "/")

    # Calculate SHA-256 hash
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    # Normalize label
    clean_label = label.strip() if label and label.strip() in ALLOWED_DOCUMENT_LABELS else "Supporting Document"

    # Extract text content
    extracted_text, extraction_status, diagnostic_notes = extract_document_text(file_bytes, file_type)

    # 1. Write file bytes to disk
    try:
        with open(abs_file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        logger.error("Failed writing document to disk: %s", e)
        return False, None, f"Disk write failure: {e}"

    # 2. Insert into database with rollback guard (Requirement 13)
    try:
        clean_original_name = secure_filename(original_filename) or f"document.{ext}"

        document = Document(
            filename=storage_filename,
            original_name=clean_original_name,
            file_path=rel_file_path,
            file_size=len(file_bytes),
            file_type=file_type,
            label=clean_label,
            description=description.strip() if description else None,
            extracted_text=extracted_text if extracted_text else None,
            extraction_status=extraction_status,
            sha256_hash=sha256,
            uploaded_by=uploader_id
        )
        db.session.add(document)
        db.session.flush()

        # If notice_id provided, create junction record
        if notice_id:
            notice = Notice.query.get(notice_id)
            if notice:
                nd = NoticeDocument(
                    notice_id=notice.id,
                    document_id=document.id,
                    display_label=(display_label or clean_label).strip()
                )
                db.session.add(nd)

        db.session.commit()
        logger.info("Saved document id=%d (%s) status=%s", document.id, document.filename, extraction_status)
        return True, document, f"Document uploaded successfully ({diagnostic_notes})."

    except Exception as e:
        db.session.rollback()
        # Clean up physical file on database failure (Requirement 13)
        if os.path.exists(abs_file_path):
            try:
                os.remove(abs_file_path)
            except Exception as rm_err:
                logger.error("Failed to remove orphan file %s: %s", abs_file_path, rm_err)

        logger.error("Database failure while saving document: %s", e)
        return False, None, f"Database transaction failed: {e}"


def delete_document(document: Document) -> Tuple[bool, str]:
    """
    Safely removes document database records and cascades junction deletions,
    then removes physical bytes from storage.
    """
    if not document:
        return False, "Document not found."

    upload_dir = current_app.config.get("DOCUMENTS_UPLOAD_FOLDER")
    abs_file_path = os.path.join(upload_dir, document.filename) if upload_dir else None

    try:
        name = document.original_name
        db.session.delete(document)
        db.session.commit()

        # Remove physical file
        if abs_file_path and os.path.exists(abs_file_path):
            try:
                os.remove(abs_file_path)
            except Exception as rm_err:
                logger.warning("Could not delete physical file %s: %s", abs_file_path, rm_err)

        return True, f"Document '{name}' deleted successfully."

    except Exception as e:
        db.session.rollback()
        return False, f"Failed to delete document: {e}"
