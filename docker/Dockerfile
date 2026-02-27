FROM python:3.11-slim

# System deps for PyMuPDF/pymupdf4llm, pdf2image, Tesseract
# libgl1 + libglib2.0-0: required by opencv-python-headless (pymupdf4llm[layout])
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY src/ src/
COPY tests/ tests/

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
