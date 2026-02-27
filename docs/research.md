# docu-flow — Research Document
## PDF Parsing & AI Stack for Clinical Trial Protocol Pre-Screening

**Date:** February 2026
**Scope:** Technical research to support the design of a fast, cost-efficient pre-screening funnel for clinical trial recruitment.

---

## Problem Statement

Clinical trial recruitment is bottlenecked by a manual, expensive process: coordinators must read lengthy protocol documents (50–200+ pages), extract eligibility criteria, and screen candidates against them.

**The core insight — Pareto filter:** A small subset of criteria (~top 8 disqualifying factors) eliminates ~80% of candidates upfront. Automating this pre-filter at high speed and low cost creates a funnel that only surfaces likely-qualified candidates for expensive human review.

**The pipeline:**

```
Protocol PDF (50–200 pages)
  ↓
Parse & extract eligibility criteria section
  ↓
Identify top ~8 disqualifying factors (LLM-ranked)
  ↓
Screen patient record against disqualifiers
  ↓
Disqualify (80% fast exit) ─── or ─── Pass to full human review (20%)
```

**Two distinct AI tasks:**
1. **Protocol parsing** — one-time per protocol; extract and structure eligibility criteria
2. **Patient screening** — high-volume, repeated; apply criteria against patient records

These have different latency, cost, and accuracy requirements and should be treated as separate pipeline stages.

---

## Stage 1: Protocol PDF Parsing

### Document Characteristics

Clinical trial protocols are almost exclusively **digitally-born PDFs** (generated from Word or LaTeX by pharmaceutical companies and CROs). This is the best-case scenario for parsing:

- Native text layer is present and accurate
- No OCR needed in the vast majority of cases
- Structure is consistent: numbered sections, defined headings (Section 4/5/6 is typically Eligibility Criteria in ICH E6 format)
- Tables appear in inclusion/exclusion lists (lab value ranges, age brackets, diagnostic codes)
- 50–200 pages means content exceeds typical LLM context windows but is manageable with sectioning

**Rare exceptions requiring OCR fallback:** older protocols scanned from paper, or protocols submitted as image-embedded PDFs by some sponsors.

---

### Recommended Parser: Docling

**Docling (IBM / Linux Foundation AI & Data) — MIT license**

Docling is the recommended primary parser for this use case for the following reasons:

| Criterion | Why Docling Wins |
|---|---|
| Table accuracy | 97.9% on complex table benchmark — critical for lab value tables in eligibility criteria |
| Structure output | JSON with element types (section_header, text, table, list_item) + heading levels + bounding boxes |
| Reading order | Handles multi-column layouts correctly (some protocols use two-column appendices) |
| Section detection | H1–H4 hierarchy preserved; eligibility criteria section can be located by heading text match |
| License | MIT — fully commercial-friendly, no royalty or disclosure obligations |
| Self-hosted | Runs fully on-premise; no patient/protocol data leaves the environment (critical for HIPAA) |
| LLM integrations | Native LangChain, LlamaIndex, Haystack integration |

**Key Docling capabilities for this pipeline:**

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("protocol.pdf")

# Access structured JSON with full hierarchy
doc_json = result.document.export_to_dict()

# Export to Markdown (H1/H2/H3 headings preserved)
markdown = result.document.export_to_markdown()

# Use HierarchicalChunker for RAG-ready chunks with metadata
from docling.chunking import HierarchicalChunker
chunker = HierarchicalChunker()
chunks = list(chunker.chunk(result.document))
# Each chunk has: text, metadata.headings[], metadata.page_numbers[]
```

**Speed:** ~1.3s/page on Apple Silicon (M-series), ~0.49s/page on Nvidia GPU. A 100-page protocol takes ~2 minutes CPU / ~50 seconds GPU. This is acceptable for a one-time extraction step.

---

### Alternative Parsers (and when to use them)

**PyMuPDF (`fitz`) + `pymupdf4llm`**
- Use for: rapid prototyping, pre-filtering (fast scan to detect if the protocol has a text layer before running Docling)
- Advantage: sub-second full-document extraction; the `pymupdf4llm` extension outputs LLM-ready Markdown
- Limitation: table detection less robust than Docling's TableFormer; no hierarchy metadata
- License: AGPL v3 (requires commercial license for proprietary use)

```python
import pymupdf4llm
md = pymupdf4llm.to_markdown("protocol.pdf")  # Full protocol as Markdown in <1s
```

**pdfplumber**
- Use for: debugging extraction issues; visual inspection of bounding boxes
- `page.to_image()` renders the page with overlaid extraction results — invaluable for verifying table extraction
- Keep this in the toolchain as a diagnostic aid, not the primary extractor

**OCRmyPDF + Surya (OCR fallback)**
- Use for: the rare scanned or image-embedded protocol
- Detection: if `PyMuPDF page.get_text()` returns <50 chars on a content-rich page, route to OCR
- OCRmyPDF handles preprocessing (deskew, denoise, binarization) then embeds text back into the PDF
- Surya provides 97.7% OCR accuracy across 90+ languages

```python
import fitz  # PyMuPDF

def needs_ocr(pdf_path: str) -> bool:
    doc = fitz.open(pdf_path)
    for page in doc:
        text = page.get_text().strip()
        if len(text) < 50:
            return True
    return False
```

---

### Extracting the Eligibility Criteria Section

Clinical trial protocols follow a consistent structure (ICH E6 / ICH E8 format). The eligibility criteria section is almost always titled "Inclusion Criteria" / "Exclusion Criteria" or "Eligibility Criteria" and appears as a numbered list under Section 4, 5, or 6.

**Extraction strategy:**

1. Parse with Docling → get JSON with labeled elements and heading hierarchy
2. Locate the eligibility section by heading text match (regex on `section_header` elements)
3. Extract all `text`, `list_item`, and `table` elements under that heading until the next same-level heading
4. Pass extracted section text to LLM for structured criterion extraction

```python
import re

def extract_eligibility_section(doc_json: dict) -> list[dict]:
    """Extract elements belonging to the eligibility criteria section."""
    eligibility_pattern = re.compile(
        r"(inclusion|exclusion|eligibility|entry criteria)", re.IGNORECASE
    )
    in_section = False
    section_level = None
    elements = []

    for element in doc_json["texts"] + doc_json["tables"]:
        label = element.get("label", "")
        text = element.get("text", "")

        if label == "section_header":
            level = element.get("level", 1)
            if eligibility_pattern.search(text):
                in_section = True
                section_level = level
            elif in_section and level <= section_level:
                break  # Exited the section

        if in_section:
            elements.append(element)

    return elements
```

---

## Stage 2: Eligibility Criterion Extraction & Ranking (LLM)

### Task

Given the raw text of the eligibility criteria section, use an LLM to:
1. Parse each criterion into a structured, machine-readable form
2. Classify as inclusion or exclusion
3. Rank the top ~8 most disqualifying criteria (highest prevalence in general patient population → highest elimination rate)

This is a **one-time, per-protocol operation** — cost and latency are secondary to accuracy here.

---

### Recommended LLM: Claude 3.5 Sonnet

**Why Sonnet for criterion extraction:**

- **200K token context window** — an entire 200-page protocol fits in a single call if needed; the eligibility section alone is typically 2,000–10,000 tokens
- **Structured output fidelity** — Claude follows complex JSON schemas reliably, critical for producing machine-readable criteria
- **Medical text understanding** — understands ICD codes, lab value ranges, drug names, and clinical terminology without fine-tuning
- **Instruction following** — excels at multi-step extraction prompts ("extract each criterion, classify it, then rank by estimated population prevalence")

**Structured output with Instructor:**

```python
from anthropic import Anthropic
import instructor
from pydantic import BaseModel
from enum import Enum

class CriterionType(str, Enum):
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"

class EligibilityCriterion(BaseModel):
    id: str                          # e.g. "EX-001"
    type: CriterionType
    text: str                        # raw criterion text
    category: str                    # e.g. "age", "diagnosis", "lab_value", "medication"
    structured_condition: str        # e.g. "age >= 18", "HbA1c > 9.0%"
    estimated_prevalence_impact: float  # 0-1, fraction of general population excluded
    is_top_disqualifier: bool

class ProtocolCriteria(BaseModel):
    protocol_id: str
    trial_phase: str
    indication: str
    criteria: list[EligibilityCriterion]
    top_disqualifiers: list[str]     # IDs of top ~8 criteria by prevalence impact

client = instructor.from_anthropic(Anthropic())

def extract_criteria(eligibility_text: str, protocol_id: str) -> ProtocolCriteria:
    return client.chat.completions.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        response_model=ProtocolCriteria,
        messages=[{
            "role": "user",
            "content": f"""You are a clinical trial protocol analyst.

Extract all eligibility criteria from the following protocol text.
For each criterion:
- Assign a unique ID (IN-001 for inclusion, EX-001 for exclusion)
- Classify as inclusion or exclusion
- Identify the category (age, diagnosis, lab_value, medication, prior_treatment, etc.)
- Express as a structured condition where possible (e.g. "eGFR < 30 mL/min/1.73m²")
- Estimate the fraction of the general adult population that would be excluded by this criterion alone
- Flag the ~8 criteria with the highest estimated exclusion rate as top_disqualifier=true

Protocol ID: {protocol_id}

Eligibility Criteria Text:
{eligibility_text}"""
        }]
    )
```

**Cost estimate for extraction:** A 10,000-token eligibility section + 4,096 output tokens ≈ $0.035 per protocol using Claude Sonnet. Negligible for a one-time operation.

---

### Alternative: Two-Stage Extraction (for very complex protocols)

For protocols with unusually complex or ambiguous criteria:

1. **Stage 1** — Use PyMuPDF fast extraction to locate the eligibility section (free, instant)
2. **Stage 2** — Feed raw section to Claude Haiku for initial parse + classification (cheap, fast)
3. **Stage 3** — Feed Haiku output to Claude Sonnet for ranking and prevalence estimation (accurate, one-time)

This tiered approach keeps costs low while reserving the expensive model for the task that most benefits from it (ranking and reasoning about population prevalence).

---

## Stage 3: High-Volume Patient Screening

### Task

This is the hot path — potentially thousands of patient records screened against the top 8 disqualifying criteria per protocol. Latency and cost are the primary constraints. Accuracy remains critical (false negatives are costly: a qualified patient is incorrectly disqualified).

**Input:** Patient record (structured EHR data, unstructured clinical notes, or both)
**Input:** Pre-extracted top 8 disqualifiers for the target protocol
**Output:** Pass / Disqualify + reason

---

### Screening Architecture

**Option A: Rule-based (fastest, cheapest, least flexible)**

For criteria that are fully structured (age ≥ 18, HbA1c > 9.0%, eGFR < 30), apply deterministic rules extracted in Stage 2. No LLM needed for these checks.

```python
def screen_structured_criteria(
    patient: dict,
    criteria: list[EligibilityCriterion]
) -> tuple[bool, list[str]]:
    """Returns (is_qualified, list_of_failed_criteria)."""
    failures = []
    for criterion in criteria:
        if criterion.is_top_disqualifier and criterion.type == "exclusion":
            # Evaluate structured_condition against patient data
            if evaluate_condition(criterion.structured_condition, patient):
                failures.append(criterion.id)
    return len(failures) == 0, failures
```

Cover as many criteria as possible with rule-based checks before calling any LLM.

**Option B: LLM screening (for unstructured criteria)**

For criteria that require clinical reasoning (e.g., "clinically significant cardiovascular disease within the past 6 months," "investigator judgment"), use an LLM with the patient's clinical notes.

**Recommended model: Claude Haiku** (cheapest, fastest, 200K context)

```python
def screen_with_llm(
    patient_notes: str,
    disqualifiers: list[EligibilityCriterion],
    model: str = "claude-haiku-4-5-20251001"
) -> dict:
    criteria_text = "\n".join(
        f"- {c.id}: {c.text}" for c in disqualifiers
    )
    # Use structured output to get a reliable decision
    ...
```

**Cost per screening call:** ~2,000 tokens input (patient notes + criteria) + ~200 tokens output → ~$0.0003 per patient at Haiku pricing. At 10,000 patients: ~$3.

**Hybrid approach (recommended):** Apply rule-based filters first. If ALL top disqualifiers are satisfied by rule-based checks, decide immediately with no LLM call. Only call the LLM for patients where at least one unstructured criterion requires judgment (estimated 20–40% of the patient pool depending on criteria complexity).

---

### Latency Profile

| Stage | Tool | Latency | Cost |
|---|---|---|---|
| Protocol parsing (one-time) | Docling | 2–5 min/protocol | Free (compute only) |
| Criterion extraction (one-time) | Claude Sonnet | 3–8 sec | ~$0.03/protocol |
| Patient screening — rule-based | Python | <1 ms/patient | Free |
| Patient screening — LLM | Claude Haiku | 500–1500 ms/patient | ~$0.0003/patient |

---

## OCR Considerations

Clinical trial protocols distributed by sponsors are almost always digitally-born PDFs. However, the following scenarios require OCR:

| Scenario | Probability | Solution |
|---|---|---|
| Older protocols scanned from paper | Low (~5%) | OCRmyPDF + Surya |
| Image-embedded pages within a native PDF | Medium (~15%) | Per-page detection + Surya fallback |
| Protocols received as photographed pages | Very low | Surya or PaddleOCR + preprocessing |

**Per-page routing logic** (detect which pages need OCR):

```python
import fitz

def route_pages(pdf_path: str) -> dict[str, list[int]]:
    """Return page lists for native vs OCR processing."""
    doc = fitz.open(pdf_path)
    native_pages, ocr_pages = [], []
    for i, page in enumerate(doc):
        text_yield = len(page.get_text().strip())
        if text_yield >= 50:
            native_pages.append(i)
        else:
            ocr_pages.append(i)
    return {"native": native_pages, "ocr": ocr_pages}
```

**OCR engine recommendation: Surya**
- 97.7% accuracy (highest open-source)
- 90+ languages (covers multilingual sponsor protocols)
- Integrated into marker-pdf and usable standalone
- No cloud dependency (HIPAA-safe)

---

## Chunking Strategy for Protocol RAG (Optional Extension)

If the product evolves to support natural language questions over protocols (e.g., "What are the washout periods for prior biologics?"), the protocol needs to be chunked for a vector store.

**Recommended strategy: Hierarchical chunking with Docling**

```
Docling JSON
  ↓
HierarchicalChunker (chunk on H1→H2→H3 boundaries)
  ↓ Each chunk has metadata:
    - document_title (protocol number + study name)
    - section_h1, section_h2, section_h3 (breadcrumb)
    - page_numbers
    - element_type (text, table, list_item)
  ↓
Embed with bge-m3 or text-embedding-3-small
  ↓
Qdrant vector store (self-hosted)
  ↓
Hybrid retriever (dense vector + BM25 keyword)
```

**Chunk size:** 400–512 tokens with 10% overlap for prose; tables stay as single chunks regardless of size.

**Why hierarchical over fixed-size:** A coordinator asking about eligibility criteria needs the full section context, not an arbitrary 512-token window. Section-boundary chunks keep clinically coherent units together and carry section breadcrumbs that allow metadata filtering (e.g., filter `element_type=table` for lab value queries).

---

## Recommended Tech Stack

### Core Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    # PDF parsing
    "docling>=2.0",           # primary parser, MIT license
    "pymupdf>=1.25",          # fast native extraction + page routing
    "pdfplumber>=0.11",       # debugging + table validation
    "ocrmypdf>=16.0",         # OCR fallback orchestration (wraps Tesseract)

    # LLM + structured output
    "anthropic>=0.40",        # Claude API
    "instructor>=1.5",        # Pydantic-validated LLM responses

    # Data
    "pydantic>=2.0",
    "pandas>=2.0",            # table outputs from criteria extraction

    # Embeddings + vector store (if RAG extension needed)
    # "qdrant-client>=1.10",
    # "sentence-transformers>=3.0",  # bge-m3
]
```

### Optional (OCR path)

```bash
# System-level (Homebrew on macOS)
brew install tesseract ghostscript unpaper

# Python
pip install surya-ocr easyocr
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM hallucination on criterion extraction | High — wrong criteria → wrong screening | Use structured output (Instructor + Pydantic); add human review step for extracted criteria before production use |
| False negatives in screening | High — qualified patient incorrectly excluded | Log all disqualification reasons; set confidence threshold; route borderline cases to human review |
| Protocol format variation | Medium — non-standard sections break heading detection | Fallback to full-text LLM extraction if section regex fails; maintain a format-specific override map |
| Scanned protocol pages missed | Medium — criteria on image pages not extracted | Per-page OCR detection (see routing logic above); alert coordinator if OCR was triggered |
| HIPAA / data privacy | Critical | Self-hosted Docling + local LLM option (Qwen2.5-VL-7B) for air-gapped; Claude API via BAA if cloud |
| LLM cost at scale | Low (screening is cheap) | Hybrid rule-based + LLM; Haiku for screening; cache protocol criteria extraction |

---

## Summary: Recommended Decisions

| Decision | Recommendation | Rationale |
|---|---|---|
| PDF parser | **Docling** (primary) + PyMuPDF (routing/fallback) | Best table accuracy (97.9%), MIT license, hierarchy output |
| OCR engine | **Surya** via OCRmyPDF | Highest open-source accuracy (97.7%), self-hosted |
| Criterion extraction LLM | **Claude Sonnet 4.6** | 200K context, best structured output, medical text understanding |
| Patient screening LLM | **Claude Haiku 4.5** | Cheapest + fastest for high-volume; use rule-based first |
| Structured output | **Instructor** (Pydantic) | Guaranteed schema compliance, auto-retry on violations |
| Chunking (if RAG) | **Docling HierarchicalChunker** | Section-aware, carries breadcrumb metadata |
| Vector store (if RAG) | **Qdrant** self-hosted | MIT license, fast, HIPAA-compatible |
| Framework | **LlamaIndex** or raw Anthropic SDK | LlamaIndex for RAG; SDK directly for screening pipeline |

---

## Sources

- [Docling: An Efficient Open-Source Toolkit for AI-driven Document Conversion (arXiv 2025)](https://arxiv.org/html/2501.17887v1)
- [PDF Data Extraction Benchmark 2025: Docling vs. Unstructured vs. LlamaParse](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)
- [OmniDocBench: Benchmarking Diverse PDF Document Parsing (CVPR 2025)](https://openaccess.thecvf.com/content/CVPR2025/papers/Ouyang_OmniDocBench_Benchmarking_Diverse_PDF_Document_Parsing_with_Comprehensive_Annotations_CVPR_2025_paper.pdf)
- [8 Top Open-Source OCR Models Compared](https://modal.com/blog/8-top-open-source-ocr-models-compared)
- [Comparing PyTesseract, PaddleOCR, and Surya OCR: Performance on Invoices](https://researchify.io/blog/comparing-pytesseract-paddleocr-and-surya-ocr-performance-on-invoices)
- [Instructor — Structured outputs for LLMs](https://python.useinstructor.com)
- [PyMuPDF Features Comparison](https://pymupdf.readthedocs.io/en/latest/about.html)
- [Best Chunking Strategies for RAG in 2025](https://www.firecrawl.dev/blog/best-chunking-strategies-rag)
- [RAG vs Large Context Window: Real Trade-offs for AI Apps (Redis)](https://redis.io/blog/rag-vs-large-context-window-ai-apps/)
