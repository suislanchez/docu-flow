"""Unit tests for PDF classifier (no real PDFs required — uses mocking)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docu_flow.pipeline.classifier import classify_pdf, _sample_indices
from docu_flow.schemas.pdf import PDFType


class TestSampleIndices:
    def test_fewer_pages_than_n(self):
        assert _sample_indices(5, 10) == [0, 1, 2, 3, 4]

    def test_more_pages_than_n(self):
        result = _sample_indices(100, 10)
        assert len(result) == 10
        assert result[0] == 0

    def test_exact_n(self):
        assert len(_sample_indices(10, 10)) == 10


class TestClassifyPDF:
    def _make_mock_page(self, char_count: int) -> MagicMock:
        page = MagicMock()
        page.get_text.return_value = "x" * char_count
        return page

    @patch("docu_flow.pipeline.classifier.fitz.open")
    def test_text_pdf(self, mock_open):
        doc = MagicMock()
        doc.is_encrypted = False
        doc.__len__ = lambda self: 5
        doc.__getitem__ = lambda self, i: self._make_mock_page(500)
        doc._make_mock_page = self._make_mock_page
        mock_open.return_value = doc

        # All pages have plenty of text
        pages = [self._make_mock_page(500) for _ in range(5)]
        doc.__getitem__ = lambda self, i: pages[i]
        doc.__len__ = lambda self: 5

        result = classify_pdf(Path("fake.pdf"))
        assert result == PDFType.TEXT

    @patch("docu_flow.pipeline.classifier.fitz.open")
    def test_scanned_pdf(self, mock_open):
        doc = MagicMock()
        doc.is_encrypted = False
        pages = [self._make_mock_page(0) for _ in range(5)]
        doc.__getitem__ = lambda self, i: pages[i]
        doc.__len__ = lambda self: 5
        mock_open.return_value = doc

        result = classify_pdf(Path("fake.pdf"))
        assert result == PDFType.SCANNED

    @patch("docu_flow.pipeline.classifier.fitz.open")
    def test_hybrid_pdf(self, mock_open):
        doc = MagicMock()
        doc.is_encrypted = False
        # Mix of good and bad pages
        pages = [self._make_mock_page(500 if i % 2 == 0 else 0) for i in range(6)]
        doc.__getitem__ = lambda self, i: pages[i]
        doc.__len__ = lambda self: 6
        mock_open.return_value = doc

        result = classify_pdf(Path("fake.pdf"))
        assert result == PDFType.HYBRID

    @patch("docu_flow.pipeline.classifier.fitz.open")
    def test_encrypted_pdf(self, mock_open):
        doc = MagicMock()
        doc.is_encrypted = True
        mock_open.return_value = doc

        result = classify_pdf(Path("fake.pdf"))
        assert result == PDFType.ENCRYPTED
