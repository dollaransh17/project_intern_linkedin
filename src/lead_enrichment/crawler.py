"""Resilient browser crawler that returns rendered, readable page text."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse

from .schemas import CrawlPage, PipelineError

RELEVANT_TERMS = (
    "about",
    "team",
    "leadership",
    "company",
    "contact",
    "pricing",
    "customers",
    "careers",
)
SKIPPED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".mp4")
BOT_BLOCKER_TERMS = ("captcha", "access denied", "verify you are human", "unusual traffic")


@dataclass(frozen=True)
class CrawlResult:
    pages: list[CrawlPage]
    errors: list[PipelineError]


class _VisibleTextParser(HTMLParser):
    """Small dependency-free fallback parser for when a browser cannot launch."""

    removed_tags = {"script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form"}

    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self._removed_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        if tag in self.removed_tags:
            self._removed_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = dict(attributes).get("href")
            if href:
                self.links.append(urljoin(self.page_url, href))

    def handle_endtag(self, tag: str) -> None:
        if tag in self.removed_tags and self._removed_depth:
            self._removed_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if not self._removed_depth:
            self.text_parts.append(data)


class SiteCrawler:
    """Crawl a homepage and a bounded set of relevant same-site links."""

    def __init__(self, timeout_ms: int, max_subpages: int, use_browser: bool = True) -> None:
        self.timeout_ms = timeout_ms
        self.max_subpages = max_subpages
        self.use_browser = use_browser

    def crawl(self, homepage_url: str) -> CrawlResult:
        if not self.use_browser:
            return self._crawl_with_http(homepage_url)
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            return CrawlResult(
                pages=[],
                errors=[
                    PipelineError(
                        stage="browser_setup",
                        message="Playwright is not installed. Run `playwright install chromium` after installing requirements.",
                        url=homepage_url,
                    )
                ],
            )

        pages: list[CrawlPage] = []
        errors: list[PipelineError] = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (compatible; LeadEnrichmentAssignment/1.0; "
                        "+https://github.com/your-username/autonomous-lead-enrichment-agent)"
                    )
                )
                page = context.new_page()
                homepage, homepage_links, homepage_errors = self._load_page(
                    page, homepage_url, PlaywrightTimeoutError, PlaywrightError
                )
                errors.extend(homepage_errors)
                if homepage is not None:
                    pages.append(homepage)

                for candidate_url in self._select_relevant_links(homepage_url, homepage_links):
                    crawled_page, _, page_errors = self._load_page(
                        page, candidate_url, PlaywrightTimeoutError, PlaywrightError
                    )
                    errors.extend(page_errors)
                    if crawled_page is not None:
                        pages.append(crawled_page)

                context.close()
                browser.close()
        except PlaywrightError as error:
            errors.append(
                PipelineError(
                    stage="browser_fallback",
                    message=f"Browser could not launch; used HTTP text fallback. {self._short_error(error)}",
                    url=homepage_url,
                )
            )
            fallback_result = self._crawl_with_http(homepage_url)
            pages.extend(fallback_result.pages)
            errors.extend(fallback_result.errors)
        except Exception as error:
            errors.append(
                PipelineError(
                    stage="browser_fallback",
                    message=f"Browser runtime failed; used HTTP text fallback. {self._short_error(error)}",
                    url=homepage_url,
                )
            )
            fallback_result = self._crawl_with_http(homepage_url)
            pages.extend(fallback_result.pages)
            errors.extend(fallback_result.errors)

        return CrawlResult(pages=pages, errors=errors)

    def _crawl_with_http(self, homepage_url: str) -> CrawlResult:
        pages: list[CrawlPage] = []
        errors: list[PipelineError] = []
        homepage, homepage_links, homepage_errors = self._load_page_with_http(homepage_url)
        errors.extend(homepage_errors)
        if homepage is not None:
            pages.append(homepage)
        for candidate_url in self._select_relevant_links(homepage_url, homepage_links):
            crawled_page, _, page_errors = self._load_page_with_http(candidate_url)
            errors.extend(page_errors)
            if crawled_page is not None:
                pages.append(crawled_page)
        return CrawlResult(pages=pages, errors=errors)

    def _load_page_with_http(self, url: str) -> tuple[CrawlPage | None, list[str], list[PipelineError]]:
        errors: list[PipelineError] = []
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; LeadEnrichmentAssignment/1.0)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urlopen(request, timeout=self.timeout_ms / 1_000) as response:
                status_code = response.status
                page_url = response.geturl()
                content_type = response.headers.get_content_type()
                if content_type not in {"text/html", "application/xhtml+xml"}:
                    errors.append(
                        PipelineError(
                            stage="content_type",
                            message=f"Expected HTML but received {content_type}.",
                            url=page_url,
                        )
                    )
                    return None, [], errors
                charset = response.headers.get_content_charset() or "utf-8"
                html = response.read().decode(charset, errors="replace")
        except HTTPError as error:
            errors.append(PipelineError(stage="http_status", message=f"Received HTTP {error.code}.", url=url))
            return None, [], errors
        except (TimeoutError, URLError) as error:
            errors.append(PipelineError(stage="http_fallback", message=str(error), url=url))
            return None, [], errors
        except Exception as error:
            errors.append(PipelineError(stage="http_fallback", message=str(error), url=url))
            return None, [], errors

        parser = _VisibleTextParser(page_url)
        try:
            parser.feed(html)
            parser.close()
        except Exception as error:
            errors.append(PipelineError(stage="html_parse", message=str(error), url=page_url))
            return None, [], errors
        text = self._clean_text(f"{parser.title}\n{' '.join(parser.text_parts)}")
        if not text:
            errors.append(PipelineError(stage="content", message="No readable page text found.", url=page_url))
            return None, [], errors
        return (
            CrawlPage(url=page_url, title=parser.title.strip(), text=text, status_code=status_code),
            parser.links,
            errors,
        )

    def _load_page(self, page: object, url: str, timeout_error: type[Exception], browser_error: type[Exception]) -> tuple[
        CrawlPage | None, list[str], list[PipelineError]
    ]:
        errors: list[PipelineError] = []
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(self.timeout_ms, 5_000))
            except timeout_error:
                pass

            status_code = response.status if response else None
            if status_code is not None and status_code >= 400:
                errors.append(
                    PipelineError(stage="http_status", message=f"Received HTTP {status_code}.", url=url)
                )
                return None, [], errors

            payload = page.evaluate(
                """() => {
                    const copy = document.body.cloneNode(true);
                    copy.querySelectorAll('script, style, noscript, svg, nav, header, footer, aside, form').forEach(
                        element => element.remove()
                    );
                    const description = document.querySelector('meta[name="description"]')?.content || '';
                    return {
                        title: document.title || '',
                        text: copy.innerText || '',
                        links: Array.from(document.querySelectorAll('a[href]')).map(anchor => ({
                            href: anchor.href,
                            text: (anchor.innerText || anchor.getAttribute('aria-label') || '').trim()
                        }))
                    };
                }"""
            )
            text = self._clean_text(f"{payload['title']}\n{payload['text']}")
            if not text:
                errors.append(PipelineError(stage="content", message="No readable page text found.", url=url))
                return None, [], errors

            lower_text = text.lower()
            if any(term in lower_text for term in BOT_BLOCKER_TERMS):
                errors.append(
                    PipelineError(
                        stage="bot_blocker_warning",
                        message="Page text may indicate a bot challenge; extracted data may be incomplete.",
                        url=url,
                    )
                )

            links = [item["href"] for item in payload["links"] if item["href"]]
            return (
                CrawlPage(url=page.url, title=payload["title"].strip(), text=text, status_code=status_code),
                links,
                errors,
            )
        except timeout_error:
            errors.append(PipelineError(stage="timeout", message="Page load timed out.", url=url))
        except browser_error as error:
            errors.append(PipelineError(stage="page_load", message=str(error), url=url))
        except Exception as error:
            errors.append(PipelineError(stage="page_load", message=str(error), url=url))
        return None, [], errors

    def _select_relevant_links(self, homepage_url: str, links: list[str]) -> list[str]:
        homepage_host = self._registrable_host(homepage_url)
        candidates: list[tuple[int, str]] = []
        seen: set[str] = {self._canonical_url(homepage_url)}
        for link in links:
            parsed = urlparse(link)
            canonical_url = self._canonical_url(link)
            if (
                parsed.scheme not in {"http", "https"}
                or self._registrable_host(link) != homepage_host
                or canonical_url in seen
                or parsed.path.lower().endswith(SKIPPED_EXTENSIONS)
            ):
                continue
            score = sum(term in f"{parsed.path} {parsed.query}".lower() for term in RELEVANT_TERMS)
            if score:
                seen.add(canonical_url)
                candidates.append((score, canonical_url))

        candidates.sort(key=lambda item: (-item[0], item[1]))
        return [url for _, url in candidates[: self.max_subpages]]

    @staticmethod
    def _clean_text(text: str) -> str:
        lines: list[str] = []
        previous_line = ""
        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            if line and line != previous_line:
                lines.append(line)
                previous_line = line
        return "\n".join(lines)

    @staticmethod
    def _canonical_url(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        return parsed._replace(fragment="", query="", path=path).geturl()

    @staticmethod
    def _registrable_host(url: str) -> str:
        host = (urlparse(url).hostname or "").lower()
        return host.removeprefix("www.")

    @staticmethod
    def _short_error(error: Exception, limit: int = 300) -> str:
        return " ".join(str(error).split())[:limit]
