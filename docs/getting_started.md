# Getting Started

## Prerequisites

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (`brew install tesseract` on macOS)
- [Poppler](https://poppler.freedesktop.org/) for pdf2image (`brew install poppler`)
- An Anthropic API key

## Local Setup

```bash
# 1. Clone / enter the project
cd docu-flow

# 2. Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install with dev extras
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

# 5. Run the API
./scripts/run_dev.sh
# → API at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

## Docker Setup (includes Redis + Celery worker)

```bash
cp .env.example .env   # set ANTHROPIC_API_KEY
docker-compose up --build
```

## CLI Usage

```bash
# Extract and display top 8 disqualifiers from a PDF
docu-flow process path/to/protocol.pdf

# Screen a patient against a protocol
docu-flow screen path/to/protocol.pdf \
  --patient '{"age": 45, "diagnoses": ["T2DM"], "HbA1c": 8.1, "is_pregnant": false}'
```

## API Usage (cURL)

```bash
# 1. Upload a protocol
PROTOCOL_ID=$(curl -s -X POST http://localhost:8000/protocols/upload \
  -F "file=@protocol.pdf" | jq -r '.protocol_id')

# 2. Poll until ready
curl http://localhost:8000/protocols/$PROTOCOL_ID

# 3. Screen a patient
curl -X POST http://localhost:8000/screening/screen \
  -H "Content-Type: application/json" \
  -d "{
    \"patient_id\": \"pt-001\",
    \"protocol_id\": \"$PROTOCOL_ID\",
    \"patient_data\": {
      \"age\": 45,
      \"diagnoses\": [\"type 2 diabetes\"],
      \"HbA1c\": 8.1,
      \"is_pregnant\": false,
      \"prior_malignancy\": false
    }
  }"
```

## Running Tests

```bash
pytest                          # all tests
pytest tests/unit/              # unit only (no LLM/PDF)
pytest tests/integration/       # integration (mocked LLM)
```
