"""Groq structured-output extraction and optional token-cost tracking."""

from __future__ import annotations

import json

from openai import OpenAI

from .config import Settings
from .schemas import CompanyIntelligence, TokenUsage

SYSTEM_PROMPT = """You extract accurate company intelligence from public website evidence.
Use only the supplied evidence. Do not infer or invent email addresses, people, titles, or LinkedIn URLs.
Return a concise company overview of exactly two sentences. For absent contacts or leadership, return an empty list.
Score confidence from 0.0 to 1.0 based solely on completeness and directness of the evidence."""


class StructuredExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    def extract(self, context: str) -> tuple[CompanyIntelligence, TokenUsage]:
        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Website evidence follows:\n\n{context}"},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "company_intelligence",
                    "strict": True,
                    "schema": CompanyIntelligence.model_json_schema(),
                },
            },
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("The LLM returned no structured content.")
        intelligence = CompanyIntelligence.model_validate(json.loads(content))
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        estimated_cost = self._estimate_cost(input_tokens, output_tokens)
        return intelligence, TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=estimated_cost,
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float | None:
        input_price = self.settings.input_usd_per_million_tokens
        output_price = self.settings.output_usd_per_million_tokens
        if input_price is None or output_price is None:
            return None
        return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
