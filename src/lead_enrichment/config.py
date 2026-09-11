"""Runtime configuration read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def _optional_nonnegative_float(name: str) -> float | None:
    raw_value = os.getenv(name)
    if raw_value in (None, ""):
        return None
    value = float(raw_value)
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    groq_model: str
    crawl_timeout_ms: int
    max_subpages: int
    max_page_chars: int
    max_context_chars: int
    input_usd_per_million_tokens: float | None
    output_usd_per_million_tokens: float | None

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required. Add it to .env or your environment.")

        return cls(
            groq_api_key=api_key,
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            crawl_timeout_ms=_positive_int("CRAWL_TIMEOUT_MS", 20_000),
            max_subpages=_positive_int("MAX_SUBPAGES", 1),
            max_page_chars=_positive_int("MAX_PAGE_CHARS", 2_000),
            max_context_chars=_positive_int("MAX_CONTEXT_CHARS", 6_000),
            input_usd_per_million_tokens=_optional_nonnegative_float(
                "GROQ_INPUT_USD_PER_MILLION_TOKENS"
            ),
            output_usd_per_million_tokens=_optional_nonnegative_float(
                "GROQ_OUTPUT_USD_PER_MILLION_TOKENS"
            ),
        )
