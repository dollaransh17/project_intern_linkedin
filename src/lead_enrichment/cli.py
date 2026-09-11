"""Command-line interface for enrichment runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import Settings
from .pipeline import enrich_domains


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enrich company domains using a rendered browser crawl and Groq.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("domains", nargs="*", help="One or more company domains or HTTP(S) URLs.")
    input_group.add_argument("--domains-file", type=Path, help="Path to a JSON array of domains.")
    parser.add_argument("--output", type=Path, default=Path("output.json"), help="Output JSON file path.")
    parser.add_argument(
        "--http-only",
        action="store_true",
        help="Skip Playwright and use the text-only resilience fallback; intended for browser-restricted environments.",
    )
    return parser


def _read_domains(arguments: argparse.Namespace, parser: argparse.ArgumentParser) -> list[str]:
    if arguments.domains_file:
        try:
            contents = json.loads(arguments.domains_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            parser.error(f"Could not read domains file: {error}")
        if not isinstance(contents, list) or not all(isinstance(item, str) for item in contents):
            parser.error("The domains file must contain a JSON array of strings.")
        return contents
    if not arguments.domains:
        parser.error("Provide at least one domain.")
    return arguments.domains


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    domains = _read_domains(arguments, parser)
    try:
        settings = Settings.from_environment()
    except ValueError as error:
        parser.error(str(error))

    output = enrich_domains(domains, settings, use_browser=not arguments.http_only)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote {len(output.results)} result(s) to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
