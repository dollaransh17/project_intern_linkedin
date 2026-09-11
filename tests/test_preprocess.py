from lead_enrichment.preprocess import build_context
from lead_enrichment.crawler import _VisibleTextParser
from lead_enrichment.schemas import CrawlPage


def test_context_keeps_source_and_email_but_not_repeated_navigation() -> None:
    page = CrawlPage(
        url="https://example.com/about",
        title="About Example",
        text="Home\nHome\nHome\nBuild fast APIs.\nsales@example.com",
        status_code=200,
    )

    context = build_context([page], max_page_chars=1_000, max_context_chars=1_000)

    assert "SOURCE URL: https://example.com/about" in context
    assert "Build fast APIs." in context
    assert "sales@example.com" in context
    assert "VISIBLE PAGE TEXT:\nHome" not in context


def test_http_fallback_parser_removes_scripts_and_makes_absolute_links() -> None:
    parser = _VisibleTextParser("https://example.com/")
    parser.feed(
        "<html><title>Example</title><body><script>secret()</script>"
        "Useful copy <a href='/about'>About</a></body></html>"
    )

    assert parser.title == "Example"
    assert "secret()" not in " ".join(parser.text_parts)
    assert "Useful copy" in " ".join(parser.text_parts)
    assert parser.links == ["https://example.com/about"]
