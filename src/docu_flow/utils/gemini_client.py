"""Google Gemini client factory.

Used for:
- Cross-validation of Anthropic-extracted criteria.
- Alternative extraction path in integration tests.
- Future: vision-based OCR on image-heavy pages (gemini-2.0-flash-exp).

Requires GOOGLE_API_KEY in environment / .env file.
"""

from __future__ import annotations

import google.generativeai as genai

from docu_flow.config import settings
from docu_flow.logging import log

_configured = False


def get_gemini_model(model: str | None = None) -> genai.GenerativeModel:
    """Return a configured Gemini GenerativeModel instance."""
    global _configured  # noqa: PLW0603

    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. "
            "Add it to .env or export it before running Google-backed tests."
        )

    if not _configured:
        genai.configure(api_key=settings.google_api_key)
        _configured = True
        log.info("gemini_client.configured", model=model or settings.gemini_model)

    return genai.GenerativeModel(model or settings.gemini_model)
