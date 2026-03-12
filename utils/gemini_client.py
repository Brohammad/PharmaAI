"""
Shared Gemini client factory using the new google-genai SDK.

Model assignment:
  Tier 1 operational (SENTINEL, PULSE, AEGIS, MERIDIAN) → gemini-3.1-flash-lite-preview
  Tier 2 validation  (CRITIQUE, COMPLIANCE)              → gemini-3.1-flash-lite-preview
  Tier 3 synthesis   (NEXUS, CHRONICLE)                  → gemini-3.1-pro-preview

All clients share one configured google.genai.Client instance (singleton).
"""

from __future__ import annotations

import os
from google import genai
from google.genai import types

from config.settings import settings

# ── Singleton client ───────────────────────────────────────────────────────────
_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Return the shared google-genai Client, creating it on first call."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


def make_generation_config(
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> types.GenerateContentConfig:
    """Build a GenerateContentConfig with PharmaIQ defaults."""
    return types.GenerateContentConfig(
        temperature=temperature if temperature is not None else settings.gemini_temperature,
        max_output_tokens=max_output_tokens if max_output_tokens is not None else settings.gemini_max_tokens,
    )


async def generate(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> str:
    """
    Async wrapper around the google-genai generate_content call.
    Returns the text of the first response candidate.
    """
    client = get_client()
    config = make_generation_config(temperature, max_output_tokens)

    response = await client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
        ),
    )
    return response.text or ""
