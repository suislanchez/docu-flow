"""Schemas for PDF parsing output."""

from enum import StrEnum

from pydantic import BaseModel, Field


class PDFType(StrEnum):
    TEXT = "text"          # native text layer, high quality
    SCANNED = "scanned"    # image-only, requires OCR
    HYBRID = "hybrid"      # mixed text + image pages
    ENCRYPTED = "encrypted"
    UNKNOWN = "unknown"


class PageText(BaseModel):
    page_number: int
    text: str
    char_count: int
    ocr_used: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ParsedDocument(BaseModel):
    source_filename: str
    pdf_type: PDFType
    total_pages: int
    pages: list[PageText]
    extraction_warnings: list[str] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def eligibility_pages(self) -> list[PageText]:
        """Pages identified as likely containing eligibility criteria."""
        return [p for p in self.pages if p.text.strip()]
