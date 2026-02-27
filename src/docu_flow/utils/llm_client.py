"""Singleton Anthropic client factory."""

from __future__ import annotations

import anthropic

from docu_flow.config import settings

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client
