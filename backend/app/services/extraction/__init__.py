"""Text extraction entry point (REQ-1.1, REQ-1.3, REQ-1.4).

Dispatch is on content sniffing first and the filename second. A browser will
happily report ``application/octet-stream`` for a .docx, and a user can rename
a .jpg to .pdf, so the declared type is treated as a hint rather than a fact.
"""

from __future__ import annotations

from app.services.extraction.base import (
    CorruptFileError,
    EncryptedFileError,
    ExtractedBlock,
    ExtractedDocument,
    ExtractionError,
    NoExtractableTextError,
    UnsupportedFormatError,
)
from app.services.extraction.docx import extract_docx
from app.services.extraction.pdf import extract_pdf
from app.services.extraction.plain import extract_plain_text

__all__ = [
    "CorruptFileError",
    "EncryptedFileError",
    "ExtractedBlock",
    "ExtractedDocument",
    "ExtractionError",
    "NoExtractableTextError",
    "UnsupportedFormatError",
    "detect_format",
    "extract",
    "extract_plain_text",
]

PDF_MAGIC = b"%PDF-"
# DOCX is a ZIP container; "PK" is the ZIP local file header signature.
ZIP_MAGIC = b"PK\x03\x04"

MIME_PDF = "application/pdf"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def detect_format(data: bytes, filename: str | None = None) -> str:
    """Return "pdf" or "docx", or raise UnsupportedFormatError.

    Magic bytes win over the extension, because the extension is user-supplied.
    """
    if data.startswith(PDF_MAGIC):
        return "pdf"

    if data.startswith(ZIP_MAGIC):
        # A .docx is a ZIP, but so is a .xlsx or a .pptx. Only a wordprocessing
        # container has word/document.xml, so check for it rather than
        # accepting any Office file.
        import zipfile

        try:
            with zipfile.ZipFile(__import__("io").BytesIO(data)) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile as exc:
            raise CorruptFileError("file is not a readable ZIP container") from exc

        if "word/document.xml" in names:
            return "docx"
        raise UnsupportedFormatError("Office file is not a Word document")

    # Legacy .doc (OLE2 compound file) is a common mistake worth naming
    # precisely, since "unsupported" would leave the user guessing.
    if data.startswith(b"\xd0\xcf\x11\xe0"):
        raise UnsupportedFormatError(
            "This looks like an older .doc file. Please save it as .docx and upload again."
        )

    suffix = (filename or "").lower().rsplit(".", 1)[-1]
    raise UnsupportedFormatError(f"unrecognised file content (extension: {suffix or 'none'})")


def extract(data: bytes, filename: str | None = None) -> ExtractedDocument:
    """Extract text from an uploaded contract.

    Raises an ``ExtractionError`` subclass whose ``error_code`` is stored on the
    contract and whose ``user_message`` is shown to the user.
    """
    if not data:
        raise CorruptFileError("file is empty")

    fmt = detect_format(data, filename)
    document = extract_pdf(data) if fmt == "pdf" else extract_docx(data)

    if document.is_empty:
        raise NoExtractableTextError("extraction produced no text")

    return document
