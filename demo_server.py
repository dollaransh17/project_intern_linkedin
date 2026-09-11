"""Local browser demo for the lead enrichment pipeline."""

from __future__ import annotations

import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
OUTPUT_PATH = PROJECT_ROOT / "output.json"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lead_enrichment.config import Settings  # noqa: E402
from lead_enrichment.pipeline import enrich_domains  # noqa: E402


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "LeadEnrichmentDemo/1.0"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._serve_file(FRONTEND_ROOT / "index.html", "text/html; charset=utf-8")
        elif path == "/styles.css":
            self._serve_file(FRONTEND_ROOT / "styles.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self._serve_file(FRONTEND_ROOT / "app.js", "application/javascript; charset=utf-8")
        elif path in {"/api/sample", "/api/output"}:
            self._send_json(self._read_output())
        else:
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/enrich":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json_body()
            domains = payload.get("domains")
            if not isinstance(domains, list) or not domains or not all(isinstance(domain, str) for domain in domains):
                raise ValueError("Enter at least one domain, one per line.")
            settings = Settings.from_environment()
            result = enrich_domains(
                domains,
                settings,
                use_browser=not bool(payload.get("http_only", True)),
            )
            OUTPUT_PATH.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            self._send_json(result.model_dump(mode="json"))
        except ValueError as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:  # Keep the browser demo responsive on unexpected failures.
            self._send_json({"error": f"Run failed: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: object) -> None:
        if self.path.startswith("/api/"):
            super().log_message(format, *args)

    def _serve_file(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "Frontend file not found."}, HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_output(self) -> dict[str, object]:
        if not OUTPUT_PATH.exists():
            return {"generated_at": None, "model": None, "results": []}
        try:
            return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return {"generated_at": None, "model": None, "results": [], "error": str(error)}

    def _read_json_body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        payload = json.loads(raw_body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.getenv("LEAD_DEMO_PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DemoHandler)
    print(f"Lead enrichment demo running at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop the demo server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
