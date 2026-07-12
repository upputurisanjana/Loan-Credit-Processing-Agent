"""
GitHub Models API client — OpenAI-compatible endpoint authenticated with a
GitHub Personal Access Token (PAT).

Usage
-----
    from app.tools.github_models_client import get_llm, call_model

Never hardcode the PAT.  Load from environment via app.config.
The token is never printed in logs.
"""

import logging
import os
import time
from typing import Any

from openai import OpenAI, RateLimitError

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default retry behaviour for GitHub Models rate limits
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # seconds; doubles each retry


def _get_client() -> OpenAI:
    """Return a configured OpenAI-compatible client pointed at GitHub Models."""
    endpoint = os.environ["GITHUB_MODELS_ENDPOINT"]
    token = os.environ["GITHUB_TOKEN"]
    # Token is deliberately not logged.
    return OpenAI(base_url=endpoint, api_key=token)


def call_model(
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 1024,
    **kwargs: Any,
) -> str:
    """
    Call the specified model on GitHub Models and return the assistant text.

    Retries on RateLimitError with exponential backoff up to _MAX_RETRIES times.
    Surfaces a clear error message rather than a raw exception if all retries
    are exhausted — the caller (graph node) should catch and move the
    application to a HOLD state rather than crashing.
    """
    client = _get_client()
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            content = response.choices[0].message.content or ""
            # Log token usage at DEBUG level without leaking the PAT
            log.debug(
                "model=%s tokens_used=%s attempt=%d",
                model,
                getattr(getattr(response, "usage", None), "total_tokens", "?"),
                attempt,
            )
            return content
        except RateLimitError as exc:
            last_exc = exc
            wait = _BACKOFF_BASE ** attempt
            log.warning(
                "GitHub Models rate limit hit (attempt %d/%d); retrying in %.1fs",
                attempt,
                _MAX_RETRIES,
                wait,
            )
            time.sleep(wait)
        except Exception as exc:  # noqa: BLE001
            # Non-retriable error — re-raise immediately
            log.error("GitHub Models call failed (model=%s): %s", model, type(exc).__name__)
            raise

    raise RuntimeError(
        f"GitHub Models call failed after {_MAX_RETRIES} retries (rate limit). "
        "Application held — please retry in a few minutes."
    ) from last_exc


def get_primary_model() -> str:
    """Return the PRIMARY_MODEL name from env (e.g. 'openai/gpt-4o-mini')."""
    return os.environ["PRIMARY_MODEL"]


def get_challenger_model() -> str:
    """Return the CHALLENGER_MODEL name from env (e.g. 'meta/llama-3.1-70b-instruct')."""
    return os.environ.get("CHALLENGER_MODEL", os.environ["PRIMARY_MODEL"])
