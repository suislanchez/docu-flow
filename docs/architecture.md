# docu-flow Architecture

## Pipeline Overview

```
Protocol PDF
    │
    ▼
┌──────────────────────┐
│  1. PDF Classifier   │  → PDFType (text / scanned / hybrid / encrypted)
└──────────┬───────────┘
           │
    ▼
┌──────────────────────┐
│  2. Text Extractor   │  → ParsedDocument (per-page text + OCR flag)
│  Adaptive strategy:  │
│  • native text first │
│  • OCR fallback/page │
└──────────┬───────────┘
           │
    ▼
┌──────────────────────┐
│  3. Section Locator  │  → SectionLocation (start/end page, confidence)
│  Heuristic regex     │
│  → LLM fallback      │
└──────────┬───────────┘
           │
    ▼
┌──────────────────────┐
│  4. Criteria         │  → ExtractedCriteria (structured JSON, citations)
│     Extractor (LLM)  │
│  Primary model +     │
│  source-page grounding│
└──────────┬───────────┘
           │
    ▼
┌──────────────────────┐
│  5. Ranker           │  → top_disqualifiers[0..8] ranked by power
│  Heuristic scoring   │
└──────────┬───────────┘
           │
    ▼
┌──────────────────────┐
│  STORED (in-memory   │
│  or Redis)           │
└──────────┬───────────┘
           │
    ▼  (per patient)
┌──────────────────────┐
│  6. Screener (LLM)   │  → ScreeningResult (disqualified / passed / escalate)
│  Top-8 filter only   │
└──────────────────────┘
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Claude Sonnet 4.6 for extraction | Best accuracy on complex medical text |
| Claude Haiku for section detection | 10x cheaper; section detection is simpler |
| Per-page OCR fallback | Avoids OCR cost on already-digital PDFs |
| Top-8 Pareto filter | Eliminates ~80% of ineligible patients cheaply |
| Source-page citations required | Prevents LLM hallucination of criteria |
| Confidence-gated escalation | Patient safety: uncertain → human review |

## Confidence Escalation Rules

- LLM screening confidence < 0.70 → `ESCALATE`
- Ambiguous criteria (is_ambiguous=True) → always flag in result
- Zero disqualifiers available → `ESCALATE`
- LLM returns unparseable JSON → `ESCALATE`

## Adding a New LLM Provider

1. Add credentials to `.env`
2. Implement an adapter in `utils/llm_client.py`
3. Update `config.py` with a `primary_llm_provider` setting
