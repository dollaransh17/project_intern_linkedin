"""Build compact, source-labelled LLM context from rendered page text."""

from __future__ import annotations

import re

from .schemas import CrawlPage

EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.IGNORECASE)
LINKEDIN_PATTERN = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/[A-Za-z0-9_./?=&%-]+", re.IGNORECASE)


def build_context(pages: list[CrawlPage], max_page_chars: int, max_context_chars: int) -> str:
    """Produce bounded text evidence; raw HTML and browser chrome never enter the prompt."""
    sections: list[str] = []
    remaining_chars = max_context_chars
    for page in pages:
        if remaining_chars <= 0:
            break
        cleaned_text = _remove_repeated_lines(page.text)
        emails = sorted(set(EMAIL_PATTERN.findall(cleaned_text)), key=str.lower)
        linkedin_urls = sorted(set(LINKEDIN_PATTERN.findall(cleaned_text)))
        evidence_lines = [
            f"SOURCE URL: {page.url}",
            f"PAGE TITLE: {page.title or '(not available)'}",
            "VISIBLE PAGE TEXT:",
            cleaned_text[:max_page_chars],
        ]
        if emails:
            evidence_lines.append(f"EMAILS FOUND ON THIS PAGE: {', '.join(emails)}")
        if linkedin_urls:
            evidence_lines.append(f"LINKEDIN URLS FOUND ON THIS PAGE: {', '.join(linkedin_urls)}")
        section = "\n".join(evidence_lines).strip()
        section = section[:remaining_chars]
        sections.append(section)
        remaining_chars -= len(section)
    return "\n\n---\n\n".join(sections)


def _remove_repeated_lines(text: str) -> str:
    """Discard repeated short navigation-style lines while preserving substantive content."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    frequencies = {line: lines.count(line) for line in set(lines)}
    return "\n".join(line for line in lines if not (len(line) < 80 and frequencies[line] > 2))
