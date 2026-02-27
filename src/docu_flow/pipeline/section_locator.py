"""
Step 3 — Locate the eligibility criteria section.

Two-pass approach:
  Pass 1 (cheap): heuristic regex scan to find candidate page range.
  Pass 2 (LLM):   if heuristics are ambiguous, send candidate pages to
                  the fast LLM to confirm / find the correct section.

Returns the slice of pages most likely to contain eligibility criteria.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from docu_flow.logging import log
from docu_flow.schemas.pdf import PageText, ParsedDocument


# Patterns that reliably indicate the eligibility section header
_SECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(inclusion|exclusion)\s+(and\s+)?(exclusion\s+)?criteria", re.IGNORECASE),
    re.compile(r"eligibility\s+criteria", re.IGNORECASE),
    re.compile(r"study\s+population", re.IGNORECASE),
    re.compile(r"patient\s+selection", re.IGNORECASE),
    re.compile(r"subject\s+selection", re.IGNORECASE),
    re.compile(r"enrollment\s+criteria", re.IGNORECASE),
]

# Stop reading when we hit one of these — they follow the criteria section
_STOP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"study\s+(procedures?|design|objectives?|endpoints?)", re.IGNORECASE),
    re.compile(r"treatment\s+(plan|regimen|administration)", re.IGNORECASE),
    re.compile(r"statistical\s+analysis", re.IGNORECASE),
    re.compile(r"pharmacokinetics", re.IGNORECASE),
]


@dataclass
class SectionLocation:
    start_page: int           # 1-indexed
    end_page: int             # 1-indexed, inclusive
    section_name: str | None
    confidence: float         # 0–1
    method: str               # "heuristic" | "llm" | "full_doc_fallback"


def locate_eligibility_section(
    document: ParsedDocument,
    llm_fallback: bool = True,
) -> SectionLocation:
    """Return the page range most likely to contain eligibility criteria."""
    location = _heuristic_locate(document)

    if location.confidence >= 0.7:
        log.info(
            "section_locator.heuristic_success",
            start=location.start_page,
            end=location.end_page,
            confidence=location.confidence,
        )
        return location

    if llm_fallback:
        log.info("section_locator.llm_fallback", confidence=location.confidence)
        location = _llm_locate(document, location)

    return location


def get_section_pages(document: ParsedDocument, location: SectionLocation) -> list[PageText]:
    """Slice pages from *document* using *location*."""
    return [
        p for p in document.pages
        if location.start_page <= p.page_number <= location.end_page
    ]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _heuristic_locate(document: ParsedDocument) -> SectionLocation:
    start_page: int | None = None
    end_page: int | None = None
    section_name: str | None = None

    for page in document.pages:
        text = page.text

        if start_page is None:
            for pattern in _SECTION_PATTERNS:
                match = pattern.search(text)
                if match:
                    start_page = page.page_number
                    section_name = match.group(0).strip()
                    break
        else:
            # Already inside section — look for stop signal
            for pattern in _STOP_PATTERNS:
                if pattern.search(text):
                    end_page = page.page_number - 1
                    break
            if end_page:
                break

    if start_page is None:
        # Fallback: use the whole document
        return SectionLocation(
            start_page=1,
            end_page=document.total_pages,
            section_name=None,
            confidence=0.1,
            method="full_doc_fallback",
        )

    end_page = end_page or min(start_page + 15, document.total_pages)
    confidence = 0.85 if section_name else 0.5

    return SectionLocation(
        start_page=start_page,
        end_page=end_page,
        section_name=section_name,
        confidence=confidence,
        method="heuristic",
    )


def _llm_locate(document: ParsedDocument, prior: SectionLocation) -> SectionLocation:
    """
    Use the fast LLM to identify which pages contain eligibility criteria.
    Sends a compact TOC-like summary of all pages to minimise tokens.
    """
    from docu_flow.utils.llm_client import get_client
    from docu_flow.config import settings

    # Build a lightweight page-snippet index (first 200 chars of each page)
    page_snippets = "\n".join(
        f"[Page {p.page_number}]: {p.text[:200].replace(chr(10), ' ')}"
        for p in document.pages
    )

    prompt = (
        "You are analysing a clinical trial protocol document. "
        "Below is a snippet from the start of each page.\n\n"
        f"{page_snippets}\n\n"
        "Identify the START page and END page (inclusive) that contain the "
        "Inclusion and Exclusion Criteria section. "
        "Reply ONLY with JSON: {\"start_page\": <int>, \"end_page\": <int>, \"section_name\": \"<string>\"}"
    )

    client = get_client()
    try:
        response = client.messages.create(
            model=settings.fast_llm_model,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        raw = response.content[0].text.strip()
        data = json.loads(raw)
        return SectionLocation(
            start_page=int(data["start_page"]),
            end_page=int(data["end_page"]),
            section_name=data.get("section_name"),
            confidence=0.75,
            method="llm",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("section_locator.llm_failed", error=str(exc))
        return prior
