# docu-flow: Clinical Trial Eligibility Screening — Project Planning Document

> **Status:** Active Planning | **Last Updated:** 2026-02-27
> **Owner:** Luis | **Stack:** TBD (see Architecture section)

---

## Problem Statement

Clinical trial recruitment is bottlenecked by a manual, expensive process: coordinators must read protocol documents (50–200+ pages), extract eligibility criteria, and screen candidates against them.

**Key insight:** A small subset of criteria — roughly the **top 8 disqualifying factors** — eliminates ~80% of candidates upfront (Pareto filter). Fast extraction and application of these criteria creates a scalable pre-screening funnel.

**Screening flow:**
```
Protocol PDF → Parse/Extract → Identify Top Disqualifiers → Screen Patient
                                                                 ↓
                                               Disqualified (80%) | Qualified → Full Human Review
```

---

## System Goals

1. Parse clinical trial protocol PDFs reliably across all format types
2. Locate and extract the eligibility criteria section
3. Identify and rank the top 8 disqualifying criteria (by disqualification power)
4. Screen a patient record against those criteria
5. Output: fast pre-screen result + confidence score + source citations
6. Escalate low-confidence cases to human review

**Non-goals (v1):**
- Replace full human review (this is a pre-screen only)
- Handle real-time EHR integration (future scope)
- Legal/regulatory sign-off automation

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────┐
│  INPUT: Protocol PDF                                │
├─────────────────────────────────────────────────────┤
│  Step 1: Classify PDF type (text/scanned/hybrid)    │
│  Step 2: Adaptive text extraction (native or OCR)   │
│  Step 3: Locate eligibility section (heuristic+LLM) │
│  Step 4: Extract criteria via LLM → structured JSON │
│  Step 5: Rank criteria by disqualification power    │
│  Step 6: Output: Top 8 disqualifiers + full list    │
├─────────────────────────────────────────────────────┤
│  SCREENING FLOW                                     │
│  Patient data → Match against top 8                 │
│    ├─ Disqualified (fast exit, ~80%)                │
│    └─ Passed → Full criteria review (human)         │
└─────────────────────────────────────────────────────┘
```

### PDF Parsing Strategy: Hybrid Adaptive (Recommended)

```
PDF
 └─ Attempt native text extraction (PyMuPDF / pdfplumber)
      └─ Quality check per page (chars/page threshold)
           ├─ Good text → proceed to section detection
           └─ Bad/no text → OCR fallback (Tesseract or cloud OCR)
 └─ Section identification (heuristic regex + LLM confirmation)
 └─ Criteria extraction (LLM, structured JSON output)
 └─ Confidence scoring + citation grounding
```

**Strategy comparison:**

| Strategy | Speed | Cost | Coverage | Notes |
|---|---|---|---|---|
| A: Text + LLM | Fast | Low | ~85% | Fails on scanned PDFs |
| B: OCR-first | Slow | High | ~99% | Overkill for native PDFs |
| **C: Hybrid Adaptive** | Medium | Medium | ~97% | **Recommended** |
| D: Vision LLM (images) | Slow | Very High | ~99% | Use only for targeted pages |
| E: ClinicalTrials.gov API | Very Fast | Free | ~60% | Use as validation supplement |

**Decision:** Implement Strategy C as the primary pipeline. Use Strategy D (vision LLM) only as a fallback for pages that fail both native extraction and OCR. Use Strategy E for cross-validation.

---

## Key Components

### 1. PDF Classifier
- Input: raw PDF bytes
- Output: `{type: "native" | "scanned" | "hybrid", page_map: {page_n: "text"|"image"}}`
- Method: check text layer density per page (< 100 chars/page → image)

### 2. Text Extractor
- Primary: `pymupdf4llm[ocr,layout]` — wraps PyMuPDF to output LLM-optimized Markdown.
  Handles multi-column reading order, tables (as Markdown tables), bold/italic, headers.
  Auto-triggers Tesseract OCR on image-only pages (no separate dispatch code needed).
- Fallback: `pdfplumber` for pages with complex merged-cell tables (pymupdf4llm drops merged cell content)
- Text repair: `ftfy.fix_text()` applied immediately after extraction — fixes mojibake,
  garbled encodings, soft hyphens, Windows-1252/Latin-1 codec confusion from PDF renderers.
- OCR cloud escalation: AWS Textract or Google Document AI for pages that fail both
  native extraction and Tesseract (e.g., low-quality scans with <50% confidence)
- Output: per-page Markdown with page numbers preserved

### 3. Section Locator
- Phase 1 — Heuristic: fuzzy match via `rapidfuzz.process.extractOne()` with `fuzz.WRatio`
  against a known header vocabulary. Handles OCR typos ("Eligibllity Criterla" → match).
  Score cutoff 80 → candidate page range.
- Phase 2 — LLM confirmation: send candidate pages, ask model to confirm and bound the section
- Handle amendments in appendices (secondary scan)

### 4. Criteria Extractor (LLM)
- Input: targeted section Markdown (3–15 pages from pymupdf4llm)
- Pre-flight: `client.messages.count_tokens()` before submission — gate on budget threshold,
  chunk if over limit. Free API call, prevents runaway cost on oversized protocols.
- Structured output: `client.messages.parse()` with Pydantic models — native constrained
  decoding (model cannot generate tokens that violate schema). No custom JSON parsing.
- Output schema (Pydantic → JSON):
  ```json
  {
    "inclusion_criteria": [
      {
        "id": "IC-01",
        "text": "Age ≥ 18 years",
        "type": "demographic",
        "logic": "threshold",
        "threshold": {"field": "age", "operator": ">=", "value": 18},
        "source_page": 12,
        "source_quote": "Patients must be 18 years of age or older"
      }
    ],
    "exclusion_criteria": [...],
    "confidence": 0.92
  }
  ```
- Grounding requirement: every criterion must cite source page + verbatim quote
- Hallucination guard: post-extraction verify each criterion's quote exists in source text

### 5. Disqualifier Ranker
- Score each exclusion criterion by estimated disqualification power
- Factors: prevalence of condition in general population, specificity of threshold, how often it appears in screening data
- Output: sorted list, top 8 highlighted

### 6. Screening Engine
- Input: patient data (structured or free-text EHR notes) + top 8 criteria JSON
- For each criterion: evaluate patient data against criterion logic
- Output per criterion: `PASS | FAIL | UNKNOWN` + confidence + reasoning
- Aggregate: if any `FAIL` with confidence > threshold → disqualify (fast exit)
- If any `UNKNOWN` → escalate to human

### 7. Confidence & Escalation Layer
- Every output carries a confidence score
- Thresholds (configurable):
  - confidence ≥ 0.85 → automated decision
  - confidence 0.60–0.85 → flag for review
  - confidence < 0.60 → mandatory human review
- Ambiguous criteria (e.g., "clinically significant") → always escalate

---

## Critical Pitfalls & Mitigations

| Pitfall | Risk Level | Mitigation |
|---|---|---|
| Silent parsing failure (garbage output) | HIGH | Per-page quality scoring; confidence gate before LLM |
| LLM hallucination of criteria | HIGH | Citation grounding; verbatim quote verification |
| Version/amendment drift | HIGH | Track protocol version; flag amendment pages |
| Over-reliance on 80% filter | HIGH | Pre-screen is never final; all passes go to full human review |
| Ambiguous criteria ("clinically significant") | MEDIUM | Flag explicitly; do not automate binary decision |
| Cost explosion on large PDFs | MEDIUM | Section-targeting first; LLM only on relevant pages |
| OCR errors in medical terminology | MEDIUM | Medical terminology correction pass post-OCR |
| Non-English protocols | LOW (v1) | Language detection + flag; translation layer in v2 |
| Encrypted/protected PDFs | LOW | Detect and reject with clear error message |

**Design principle: fail fast, fail safe, fail loud.**
- Disqualify confidently where evidence is clear
- Never silently swallow a parsing error
- Always escalate uncertainty to humans

---

## Data Models

### Protocol Record
```python
@dataclass
class Protocol:
    id: str
    title: str
    version: str
    sponsor: str
    source_pdf_path: str
    pdf_type: Literal["native", "scanned", "hybrid"]
    raw_text_by_page: dict[int, str]
    eligibility_section_pages: list[int]
    inclusion_criteria: list[Criterion]
    exclusion_criteria: list[Criterion]
    top_disqualifiers: list[Criterion]  # top 8
    extraction_confidence: float
    parsed_at: datetime
    warnings: list[str]
```

### Criterion
```python
@dataclass
class Criterion:
    id: str
    text: str
    criterion_type: Literal["inclusion", "exclusion"]
    category: str  # e.g., "demographic", "lab_value", "comorbidity", "medication"
    logic_type: Literal["threshold", "binary", "conditional", "temporal", "ambiguous"]
    structured_logic: dict | None  # machine-readable if parseable
    disqualification_power_score: float  # 0–1
    source_page: int
    source_quote: str
    confidence: float
```

### Screening Result
```python
@dataclass
class ScreeningResult:
    patient_id: str
    protocol_id: str
    screened_at: datetime
    outcome: Literal["disqualified", "passed_prescreen", "escalated"]
    criteria_results: list[CriterionResult]
    overall_confidence: float
    disqualifying_criterion_id: str | None
    escalation_reasons: list[str]
```

---

## Implementation Phases

### Phase 1 — PDF Parser & Extractor (Foundation)
- [ ] PDF classifier (text density check)
- [ ] Native text extraction (PyMuPDF)
- [ ] OCR fallback (Tesseract)
- [ ] Per-page quality scoring
- [ ] Section locator (heuristic regex)

### Phase 2 — LLM Criteria Extraction
- [ ] Prompt engineering for criteria extraction → structured JSON
- [ ] Citation grounding + quote verification
- [ ] Hallucination detection layer
- [ ] Section locator LLM confirmation pass

### Phase 3 — Screening Engine
- [ ] Criterion evaluator (threshold, binary, temporal logic)
- [ ] Top-8 ranker (disqualification power scoring)
- [ ] Screening result aggregator
- [ ] Confidence scoring + escalation logic

### Phase 4 — API & Integration
- [ ] REST API: `POST /protocols` (upload + parse), `GET /protocols/{id}/criteria`
- [ ] REST API: `POST /screen` (patient data + protocol_id → result)
- [ ] ClinicalTrials.gov cross-validation
- [ ] Audit log (all decisions + citations for traceability)

### Phase 5 — Hardening
- [ ] Amendment detection
- [ ] Multi-column / complex layout handling
- [ ] Medical terminology correction post-OCR
- [ ] Non-English protocol detection + flagging

---

## Technology Candidates

| Layer | Primary | Alternatives | Notes |
|---|---|---|---|
| PDF → LLM Markdown | `pymupdf4llm[ocr,layout]` 0.3.4 | pdfplumber, PDFMiner | Handles multi-column, tables, auto-OCR |
| Table extraction (complex) | `pdfplumber` | — | Fallback for merged-cell tables |
| OCR (native fallback) | Tesseract (via pymupdf4llm) | Surya 97.7%, PaddleOCR 96.6% | Surya preferred for scanned-heavy workloads |
| OCR (cloud escalation) | AWS Textract | Google Document AI, Azure Doc AI | For pages that fail local OCR |
| Text repair | `ftfy` 6.3.1 | — | Always-on, no deps, fixes encoding artifacts |
| Header matching | `rapidfuzz` 3.14.3 | — | Fuzzy match, OCR-typo tolerant, replaces naive regex |
| Token budgeting | `anthropic.count_tokens()` | — | Free API call; removed tiktoken dependency |
| Structured LLM output | `anthropic.messages.parse()` + Pydantic v2 | instructor | Native constrained decoding on claude-sonnet-4-6 |
| LLM (extraction) | `claude-sonnet-4-6` | claude-haiku-4-5 (fast/cheap pass) | |
| LLM (vision fallback) | `claude-sonnet-4-6` (vision) | — | Send targeted pages only |
| Language detection | `lingua-language-detector` 2.1.0 | — | Optional dep; 96 MB; for non-English protocols |
| API framework | FastAPI | — | |
| Data validation | Pydantic v2 | — | |
| Task queue | Celery + Redis | — | arq evaluated and rejected (maintenance mode) |
| External validation | ClinicalTrials.gov v2 API | — | httpx, no API key, `eligibilityModule` field |
| Complex layout (future) | Docling 2.75.0 | MinerU, marker-pdf | PyTorch dep (~1.7 GB); defer until GPU workers available |

---

## Open Questions

1. **Patient data format**: What is the input format for patient records? Structured JSON from EHR, free-text notes, or both?
2. **Disqualification power scoring**: Do we have historical screening data to train/calibrate scores, or will we use LLM-estimated prevalence initially?
3. **Regulatory context**: Is this for internal research tooling or will it interact with regulated clinical workflows (IRB implications)?
4. **Throughput requirements**: How many protocols/patients need to be processed per day?
5. **Deployment**: Cloud (AWS/GCP) or on-prem (data sensitivity)?
6. **Audit requirements**: What level of decision traceability is required?

---

## Design Constraints

- **Safety first**: The pre-screen is never a final decision. All "passed" candidates must go to full human review.
- **Citations mandatory**: Every extracted criterion must link to a verbatim source quote and page number.
- **Confidence gates**: No automated decision below the configured confidence threshold.
- **Cost control**: LLM calls are scoped to relevant sections only, never full documents.
- **Fail loud**: Parsing failures, low confidence, and ambiguous criteria must surface explicitly — never silently default to a pass or fail.
