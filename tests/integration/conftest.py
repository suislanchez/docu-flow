"""
Integration test configuration.

═══════════════════════════════════════════════════════════════════════════════
REQUIRED API KEYS
═══════════════════════════════════════════════════════════════════════════════

These integration tests call live external APIs and will be **skipped
automatically** if the required keys are absent from the environment.

  ANTHROPIC_API_KEY
    • Source:  https://console.anthropic.com/settings/keys
    • Used by: criteria extraction (claude-sonnet-4-6), section location
               fallback (claude-haiku-4-5), patient screening.
    • All tests tagged @pytest.mark.anthropic require this key.

  GOOGLE_API_KEY
    • Source:  https://aistudio.google.com/app/apikey
    • Used by: Gemini-based cross-validation of extracted criteria,
               alternative extraction path on the hard PDF.
    • All tests tagged @pytest.mark.google require this key.

Set keys in .env (copy from .env.example) or export them:

    export ANTHROPIC_API_KEY="sk-ant-..."
    export GOOGLE_API_KEY="AIza..."

Running only Anthropic tests:
    pytest tests/integration -m "integration and anthropic and not google"

Running only Google tests:
    pytest tests/integration -m "integration and google and not anthropic"

Running all integration tests:
    pytest tests/integration -m integration

Skipping slow tests (large-file processing, extensive OCR):
    pytest tests/integration -m "integration and not slow"
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os

import pytest


# ---------------------------------------------------------------------------
# Skip helpers — evaluated once per session
# ---------------------------------------------------------------------------

def _has_anthropic_key() -> bool:
    # Prefer env var; fall back to loading .env if not already set
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        return False


def _has_google_key() -> bool:
    if os.environ.get("GOOGLE_API_KEY"):
        return True
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return bool(os.environ.get("GOOGLE_API_KEY"))
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def anthropic_key() -> str:
    """
    Returns ANTHROPIC_API_KEY or skips the test.

    Required for:
      - LLM-based criteria extraction (claude-sonnet-4-6)
      - Eligibility section location via LLM fallback (claude-haiku-4-5)
      - Patient screening pipeline
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping Anthropic integration test")
    return key


@pytest.fixture(scope="session")
def google_key() -> str:
    """
    Returns GOOGLE_API_KEY or skips the test.

    Required for:
      - Gemini-based criteria extraction cross-validation
      - Alternative extraction path tested against the hard PDF
    """
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        pytest.skip("GOOGLE_API_KEY not set — skipping Google integration test")
    return key


# ---------------------------------------------------------------------------
# Auto-skip markers applied at collection time
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-skip marked tests if the required API key is missing."""
    no_anthropic = not _has_anthropic_key()
    no_google = not _has_google_key()

    for item in items:
        if no_anthropic and item.get_closest_marker("anthropic"):
            item.add_marker(
                pytest.mark.skip(reason="ANTHROPIC_API_KEY not set"),
                append=False,
            )
        if no_google and item.get_closest_marker("google"):
            item.add_marker(
                pytest.mark.skip(reason="GOOGLE_API_KEY not set"),
                append=False,
            )
