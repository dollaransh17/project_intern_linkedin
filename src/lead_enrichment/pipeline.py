"""Coordinate crawling, preprocessing, structured extraction, and JSON-ready results."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from .config import Settings
from .crawler import SiteCrawler
from .extractor import StructuredExtractor
from .preprocess import build_context
from .schemas import DomainResult, PipelineError, RunOutput


def enrich_domains(domains: list[str], settings: Settings, use_browser: bool = True) -> RunOutput:
    crawler = SiteCrawler(
        timeout_ms=settings.crawl_timeout_ms,
        max_subpages=settings.max_subpages,
        use_browser=use_browser,
    )
    extractor = StructuredExtractor(settings)
    results = [
        _enrich_one(domain=domain, crawler=crawler, extractor=extractor, settings=settings) for domain in domains
    ]
    return RunOutput(generated_at=datetime.now(UTC), model=settings.groq_model, results=results)


def _enrich_one(
    domain: str, crawler: SiteCrawler, extractor: StructuredExtractor, settings: Settings
) -> DomainResult:
    homepage_url = _normalise_domain(domain)
    if homepage_url is None:
        return DomainResult(
            domain=domain,
            pages_crawled=[],
            intelligence=None,
            errors=[PipelineError(stage="input", message="Expected a valid domain or HTTP(S) URL.", url=None)],
            token_usage=None,
        )

    crawl_result = crawler.crawl(homepage_url)
    page_urls = [page.url for page in crawl_result.pages]
    errors = list(crawl_result.errors)
    if not crawl_result.pages:
        return DomainResult(
            domain=domain,
            pages_crawled=page_urls,
            intelligence=None,
            errors=errors,
            token_usage=None,
        )

    context = build_context(
        crawl_result.pages,
        max_page_chars=settings.max_page_chars,
        max_context_chars=settings.max_context_chars,
    )
    if not context:
        errors.append(PipelineError(stage="preprocess", message="No usable page context remained.", url=homepage_url))
        return DomainResult(
            domain=domain,
            pages_crawled=page_urls,
            intelligence=None,
            errors=errors,
            token_usage=None,
        )

    try:
        intelligence, token_usage = extractor.extract(context)
    except Exception as error:
        errors.append(PipelineError(stage="llm_extraction", message=str(error), url=None))
        intelligence = None
        token_usage = None
    return DomainResult(
        domain=domain,
        pages_crawled=page_urls,
        intelligence=intelligence,
        errors=errors,
        token_usage=token_usage,
    )


def _normalise_domain(value: str) -> str | None:
    candidate = value.strip()
    if not candidate or any(character.isspace() for character in candidate):
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    hostname = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or ("." not in hostname and hostname != "localhost")
    ):
        return None
    return parsed._replace(path="/", params="", query="", fragment="").geturl()
