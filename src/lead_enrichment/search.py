"""Optional external search enrichment for leadership LinkedIn URLs."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .schemas import ExternalSearchResult


class GoogleSearchError(RuntimeError):
    """Raised when the configured Google search request cannot be completed."""


class GoogleSearchClient:
    """Look up evidence-backed LinkedIn profile URLs with Google Custom Search."""

    endpoint = "https://customsearch.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, search_engine_id: str, timeout_ms: int) -> None:
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.timeout_seconds = timeout_ms / 1_000

    def find_linkedin_profile(
        self, name: str, company_hint: str
    ) -> tuple[str | None, list[ExternalSearchResult]]:
        query = f'site:linkedin.com/in "{name}" {company_hint}'
        parameters = urlencode(
            {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": 5,
            }
        )
        request = Request(
            f"{self.endpoint}?{parameters}",
            headers={"Accept": "application/json", "User-Agent": "LeadEnrichmentAssignment/1.0"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise GoogleSearchError(f"Google search returned HTTP {error.code}.") from error
        except (URLError, TimeoutError) as error:
            raise GoogleSearchError(f"Google search request failed: {error}.") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GoogleSearchError("Google search returned an invalid JSON response.") from error

        for item in payload.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            result_url = item.get("link")
            title = str(item.get("title", "")).strip()
            snippet = str(item.get("snippet", "")).strip()
            if not isinstance(result_url, str) or not _is_linkedin_profile(result_url):
                continue
            if not _name_appears_in_result(name, result_url, title, snippet):
                continue
            result = ExternalSearchResult(
                query=query,
                title=title,
                url=result_url,
                snippet=snippet,
                provider="google_custom_search",
            )
            return result_url, [result]
        return None, []


def _is_linkedin_profile(value: str) -> bool:
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").lower()
    return hostname in {"linkedin.com", "www.linkedin.com"} and parsed.path.lower().startswith("/in/")


def _name_appears_in_result(name: str, result_url: str, title: str, snippet: str) -> bool:
    tokens = [token.lower() for token in name.split() if len(token) >= 3]
    if not tokens:
        return False
    haystack = f"{result_url} {title} {snippet}".lower()
    return all(token in haystack for token in tokens)
