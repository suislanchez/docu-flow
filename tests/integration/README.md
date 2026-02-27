# Integration Tests

These tests call live external APIs and process real clinical trial PDFs.
They are **not run by default** — they must be opted into with the `integration` marker.

---

## Test Fixtures

| File | Size | Description |
|------|------|-------------|
| `tests/fixtures/ydao_protocol_easy.pdf` | 1.8 MB | J3R-MC-YDAO protocol — native text layer, extracts cleanly. **Happy-path fixture.** |
| `tests/fixtures/large_protocol_hard.pdf` | 57 MB | Large protocol that resists standard extraction. **Stress-test / failure-mode fixture.** |

---

## Required API Keys

### `ANTHROPIC_API_KEY`
- **Obtain:** <https://console.anthropic.com/settings/keys>
- **Used by:** `claude-sonnet-4-6` (criteria extraction, patient screening) and `claude-haiku-4-5` (section location LLM fallback)
- **Tests tagged:** `@pytest.mark.anthropic`

### `GOOGLE_API_KEY`
- **Obtain:** <https://aistudio.google.com/app/apikey>
- **Used by:** `gemini-2.0-flash` for cross-validation of extracted criteria and alternative extraction on the hard PDF
- **Tests tagged:** `@pytest.mark.google`

### Setting keys

Copy `.env.example` → `.env` and fill in your keys:

```bash
cp .env.example .env
# edit .env — set ANTHROPIC_API_KEY and GOOGLE_API_KEY
```

Or export directly:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
```

Tests skip automatically if a required key is absent — they do not fail.

---

## Running the Tests

```bash
# All integration tests (both APIs)
pytest tests/integration -m integration -v

# Anthropic only
pytest tests/integration -m "integration and anthropic and not google" -v

# Google only
pytest tests/integration -m "integration and google and not anthropic" -v

# Skip slow tests (large file OCR, extended processing)
pytest tests/integration -m "integration and not slow" -v

# Easy PDF only
pytest tests/integration/test_easy_pdf.py -m integration -v

# Hard PDF only
pytest tests/integration/test_hard_pdf.py -m integration -v

# With live output (recommended for integration tests)
pytest tests/integration -m integration -v -s
```

---

## Test Coverage by Stage

### Easy PDF (`test_easy_pdf.py`)

| Test | API Key | Stage |
|------|---------|-------|
| `test_classify_easy_pdf` | none | PDF classification |
| `test_extract_text_easy_pdf` | none | Text extraction |
| `test_extraction_warnings_easy_pdf` | none | Warning surfacing |
| `test_locate_eligibility_section_easy_pdf` | none | Section location (heuristic) |
| `test_section_pages_non_empty` | none | Section page slicing |
| `test_extract_criteria_easy_pdf` | ANTHROPIC | LLM criteria extraction |
| `test_criteria_verbatim_in_source` | ANTHROPIC | Hallucination guard |
| `test_full_pipeline_easy_pdf` | ANTHROPIC | End-to-end pipeline |
| `test_screening_disqualified_patient` | ANTHROPIC | Screening — ineligible patient |
| `test_screening_likely_eligible_patient` | ANTHROPIC | Screening — eligible patient |
| `test_gemini_criteria_extraction_easy_pdf` | GOOGLE | Gemini extraction |
| `test_anthropic_gemini_criteria_count_agreement` | ANTHROPIC + GOOGLE | Cross-model validation |

### Hard PDF (`test_hard_pdf.py`)

| Test | API Key | Slow | Stage |
|------|---------|------|-------|
| `test_classify_hard_pdf` | none | no | Classification |
| `test_classify_hard_pdf_not_unknown` | none | no | Classification sanity |
| `test_extract_hard_pdf_does_not_crash` | none | yes | Crash safety |
| `test_extraction_warnings_surface_for_hard_pdf` | none | yes | Error surfacing |
| `test_hard_pdf_text_quality_score` | none | yes | Quality metrics |
| `test_section_locator_hard_pdf_heuristic` | none | yes | Section location |
| `test_gemini_extraction_hard_pdf` | GOOGLE | yes | Gemini on hard PDF |
| `test_anthropic_extraction_hard_pdf` | ANTHROPIC | yes | Full pipeline on hard PDF |

---

## Understanding `xfail` Results

Several hard-PDF tests are marked `pytest.xfail` rather than `pytest.fail`.
This is intentional:

- The hard PDF **is expected to partially fail** — that is the point.
- `xfail` means "this is a known-difficult case; failure here is informative, not a bug."
- If the hard PDF test **unexpectedly passes** (`xpass`), that's a win worth noting.
- If it raises an **unhandled exception** (not `ExtractionError`), that is a real bug.

---

## Safety Rules Tested

These integration tests enforce the non-negotiable safety rules from `PLANNING.md`:

1. **Errors surface loudly** — `test_extraction_warnings_surface_for_hard_pdf`
2. **Citation grounding** — `test_extract_criteria_easy_pdf`, `test_criteria_verbatim_in_source`
3. **Hallucination guard** — `test_criteria_verbatim_in_source`
4. **Pre-screen is never final** — decision field always checked, never assumed
5. **Cross-model validation** — `test_anthropic_gemini_criteria_count_agreement`
