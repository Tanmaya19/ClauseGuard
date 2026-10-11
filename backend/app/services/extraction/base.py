"""Shared types for text extraction (REQ-1.3, REQ-1.4)."""

from __future__ import annotations

from dataclasses import dataclass, field


class ExtractionError(Exception):
    """Base class for extraction failures.

    ``error_code`` is persisted on the contract and maps to user-facing copy in
    the frontend, so it is part of the API contract — do not rename codes
    without updating the UI.
    """

    error_code = "extraction_failed"
    user_message = "We could not read this file. Please try a different copy."


class UnsupportedFormatError(ExtractionError):
    """REQ-1.1: only PDF and DOCX are accepted."""

    error_code = "unsupported_format"
    user_message = "Only PDF and Word (.docx) files can be analysed."


class NoExtractableTextError(ExtractionError):
    """REQ-1.4: a scanned or image-only document.

    OCR is deliberately out of scope for V1.0 (TBD-7), so this is a terminal
    condition rather than a fallback path.
    """

    error_code = "no_extractable_text"
    user_message = (
        "This file appears to be a scan or a picture of a contract, so there is no "
        "text we can read. Please upload a text-based PDF or Word version — usually "
        "the file your counterparty emailed you, rather than a photo or a scan."
    )


class EncryptedFileError(ExtractionError):
    error_code = "encrypted_file"
    user_message = (
        "This file is password-protected. Please remove the password and upload it again."
    )


class CorruptFileError(ExtractionError):
    error_code = "corrupt_file"
    user_message = "This file could not be opened. It may be damaged or incomplete."


@dataclass(slots=True)
class ExtractedBlock:
    """A paragraph-ish run of text with its offsets into the assembled document.

    Carrying ``is_heading`` out of extraction matters: a PDF heading is
    identifiable from font size and weight, but that signal is gone once the
    page is flattened to a string. Segmentation (REQ-2.1) uses it, so it is
    captured here while it still exists.
    """

    text: str
    char_start: int
    char_end: int
    page: int | None = None
    is_heading: bool = False


@dataclass(slots=True)
class ExtractedDocument:
    text: str
    blocks: list[ExtractedBlock] = field(default_factory=list)
    page_count: int | None = None

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()
