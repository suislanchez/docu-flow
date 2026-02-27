"""
Step 3 — Locate the eligibility criteria section.

Strategy (in priority order):
  1. Parse the Table of Contents (usually first ~10 pages) and read the page
     number for the eligibility/inclusion/exclusion criteria entry.
  2. Fall back to a heuristic body-text scan if no TOC is found.
  3. Fall back to the fast LLM if heuristics are ambiguous.

Returns the slice of pages most likely to contain eligibility criteria.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from docu_flow.logging import log
from docu_flow.schemas.pdf import PageText, ParsedDocument


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Keywords we look for in the TOC and body text
_CRITERIA_KEYWORDS: list[re.Pattern[str]] = [
    re.compile(r"(inclusion|exclusion)\s+(and\s+)?(exclusion\s+)?criteria", re.IGNORECASE),
    re.compile(r"eligibility\s+criteria", re.IGNORECASE),
    re.compile(r"enrollment\s+criteria", re.IGNORECASE),
    re.compile(r"study\s+population", re.IGNORECASE),
    re.compile(r"patient\s+selection", re.IGNORECASE),
    re.compile(r"subject\s+selection", re.IGNORECASE),
]

# TOC line: keyword text followed by dot-leaders and a page number.
# Captures: (section_name, page_number)
# Examples:
#   "Inclusion Criteria ............................................45"
#   "5.1  Exclusion Criteria ....... 46"
_TOC_ENTRY_PATTERN = re.compile(
    r"(?P<name>"
    r"(?:inclusion|exclusion)(?:\s+(?:and\s+)?(?:exclusion\s+)?)?criteria"
    r"|eligibility\s+criteria"
    r"|enrollment\s+criteria"
    r"|study\s+population"
    r"|patient\s+selection"
    r"|subject\s+selection"
    r")"
    r"\s*\.{3,}\s*(?P<page>\d{1,4})",
    re.IGNORECASE,
)

# Explicit TOC header
_TOC_HEADER_PATTERN = re.compile(r"table\s+of\s+contents", re.IGNORECASE)

# Dot-leader lines (for detecting TOC pages)
_TOC_DOT_LEADER_PATTERN = re.compile(r"\.{4,}\s*\d{1,3}\s*$", re.MULTILINE)

# Stop reading when we hit one of these — they follow the criteria section
_STOP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:^|\n)\s*\d*\.?\d*\.?\s*(?:study\s+(?:procedures?|design|objectives?|endpoints?)|treatment\s+(?:plan|regimen|administration)|statistical\s+(?:analysis|considerations)|pharmacokinetics)", re.IGNORECASE),
]

# Max pages to scan for TOC
_TOC_SCAN_LIMIT = 12


@dataclass
class SectionLocation:
    start_page: int           # 1-indexed
    end_page: int             # 1-indexed, inclusive
    section_name: str | None
    confidence: float         # 0–1
    method: str               # "toc" | "heuristic" | "llm" | "full_doc_fallback"


def locate_eligibility_section(
    document: ParsedDocument,
    llm_fallback: bool = True,
) -> SectionLocation:
    """Return the page range most likely to contain eligibility criteria."""

    # --- Pass 1: Parse TOC (fast, high confidence) ---
    location = _toc_locate(document)
    if location is not None:
        log.info(
            "section_locator.toc_success",
            start=location.start_page,
            end=location.end_page,
            section=location.section_name,
        )
        return location

    # --- Pass 2: Heuristic body-text scan ---
    location = _heuristic_locate(document)
    if location is not None and location.confidence >= 0.7:
        log.info(
            "section_locator.heuristic_success",
            start=location.start_page,
            end=location.end_page,
            confidence=location.confidence,
        )
        return location

    # --- Pass 3: LLM fallback ---
    if llm_fallback:
        prior = location or SectionLocation(1, document.total_pages, None, 0.1, "full_doc_fallback")
        log.info("section_locator.llm_fallback", confidence=prior.confidence)
        return _llm_locate(document, prior)

    return location or SectionLocation(1, document.total_pages, None, 0.1, "full_doc_fallback")


def get_section_pages(document: ParsedDocument, location: SectionLocation) -> list[PageText]:
    """Slice pages from *document* using *location*."""
    return [
        p for p in document.pages
        if location.start_page <= p.page_number <= location.end_page
    ]


# ---------------------------------------------------------------------------
# Pass 1 — Table of Contents
# ---------------------------------------------------------------------------

def _toc_locate(document: ParsedDocument) -> SectionLocation | None:
    """Scan the first few pages for a TOC entry pointing to eligibility criteria."""
    toc_pages = [p for p in document.pages if p.page_number <= _TOC_SCAN_LIMIT]

    # Collect all matching TOC entries across TOC pages
    entries: list[tuple[str, int]] = []  # (section_name, target_page)

    for page in toc_pages:
        if not _is_toc_page(page.text):
            continue
        for match in _TOC_ENTRY_PATTERN.finditer(page.text):
            name = match.group("name").strip()
            target = int(match.group("page"))
            entries.append((name, target))
            log.debug("section_locator.toc_entry", name=name, target_page=target)

    if not entries:
        return None

    # Pick the earliest criteria-specific entry as start page.
    # Sort: prefer "inclusion/exclusion criteria" over "study population".
    def _specificity(entry: tuple[str, int]) -> tuple[int, int]:
        name_lower = entry[0].lower()
        if "inclusion" in name_lower or "exclusion" in name_lower:
            return (0, entry[1])  # most specific, sort by page
        if "eligib" in name_lower or "enrollment" in name_lower:
            return (1, entry[1])
        return (2, entry[1])  # generic: study population, etc.

    entries.sort(key=_specificity)
    best_name, start_page = entries[0]

    # End page: use the latest TOC entry page number + a buffer,
    # or scan for a stop pattern from the actual pages.
    last_entry_page = max(e[1] for e in entries)
    end_page = _find_end_page(document.pages, start_page, document.total_pages)

    # Make sure we include at least up to the last TOC-listed criteria page
    end_page = max(end_page, last_entry_page)

    return SectionLocation(
        start_page=start_page,
        end_page=end_page,
        section_name=best_name,
        confidence=0.95,
        method="toc",
    )


# ---------------------------------------------------------------------------
# Pass 2 — Heuristic body-text scan
# ---------------------------------------------------------------------------

def _heuristic_locate(document: ParsedDocument) -> SectionLocation | None:
    """Scan body pages for section headers with criteria keywords."""
    pages = document.pages
    page_map = {p.page_number: p for p in pages}

    for page in pages:
        text = page.text
        if _is_toc_page(text):
            continue
        for pattern in _CRITERIA_KEYWORDS:
            match = pattern.search(text)
            if match:
                start_page = page.page_number
                end_page = _find_end_page(pages, start_page, document.total_pages)
                item_count = _count_criteria_items(page_map, start_page, end_page)
                if item_count >= 5:
                    return SectionLocation(
                        start_page=start_page,
                        end_page=end_page,
                        section_name=match.group(0).strip(),
                        confidence=0.80,
                        method="heuristic",
                    )
                break  # this page didn't have enough items, keep scanning

    return None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _find_end_page(pages: list[PageText], start_page: int, total_pages: int) -> int:
    """Scan forward from *start_page* for a stop pattern and return end page."""
    for page in pages:
        if page.page_number <= start_page:
            continue
        for pattern in _STOP_PATTERNS:
            if pattern.search(page.text):
                return page.page_number - 1
    return min(start_page + 15, total_pages)


def _count_criteria_items(
    page_map: dict[int, PageText],
    start_page: int,
    end_page: int,
) -> int:
    """Count distinct numbered-list items in the section."""
    numbered = re.compile(r"^\s*\d+[\.\)]\s", re.MULTILINE)
    total = 0
    for pn in range(start_page, end_page + 1):
        page = page_map.get(pn)
        if page:
            total += len(numbered.findall(page.text))
    return total


def _is_toc_page(text: str) -> bool:
    """Return True if this page looks like a table of contents."""
    if _TOC_HEADER_PATTERN.search(text):
        return True
    dot_leader_lines = len(_TOC_DOT_LEADER_PATTERN.findall(text))
    return dot_leader_lines >= 3


# ---------------------------------------------------------------------------
# Pass 3 — LLM fallback
# ---------------------------------------------------------------------------

def _llm_locate(document: ParsedDocument, prior: SectionLocation) -> SectionLocation:
    """Use the fast LLM to identify which pages contain eligibility criteria."""
    from docu_flow.utils.llm_client import get_client
    from docu_flow.config import settings
    import json

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
        'Reply ONLY with JSON: {"start_page": <int>, "end_page": <int>, "section_name": "<string>"}'
    )

    client = get_client()
    try:
        response = client.messages.create(
            model=settings.fast_llm_model,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
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
