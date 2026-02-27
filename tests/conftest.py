"""
Root test configuration.

Provides path fixtures for the two canonical test PDFs and registers
custom pytest markers so they do not trigger PytestUnknownMarkWarning.

Test fixtures
─────────────
easy_pdf_path  →  tests/fixtures/ydao_protocol_easy.pdf
                  J3R-MC-YDAO clinical trial protocol (~1.8 MB).
                  Native-text PDF that extracts cleanly — the happy path.

hard_pdf_path  →  tests/fixtures/large_protocol_hard.pdf
                  Large (~57 MB) protocol that resists standard extraction.
                  Used to validate OCR fallback, error surfacing, and
                  graceful degradation behaviour.
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path constants (used by all test layers)
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"

EASY_PDF = FIXTURES_DIR / "ydao_protocol_easy.pdf"
HARD_PDF = FIXTURES_DIR / "large_protocol_hard.pdf"


# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def easy_pdf_path() -> Path:
    """Path to the parseable YDAO protocol PDF (happy-path fixture)."""
    assert EASY_PDF.exists(), f"Easy PDF fixture missing: {EASY_PDF}"
    return EASY_PDF


@pytest.fixture(scope="session")
def hard_pdf_path() -> Path:
    """Path to the large/problematic protocol PDF (stress-test fixture)."""
    assert HARD_PDF.exists(), f"Hard PDF fixture missing: {HARD_PDF}"
    return HARD_PDF
