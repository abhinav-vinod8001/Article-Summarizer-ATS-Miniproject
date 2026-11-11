"""Vercel Python serverless endpoint for summarizing article text."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from groq import Groq
from summarizer import compute_stats, summarize

PUBLIC_DIR = ROOT_DIR / "public"
MAX_BODY_BYTES = 262_144  # 256 KB
MAX_WORDS = 15_000
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


def process_summarization(payload: Any, api_key: str) -> Tuple[int, Dict[str, Any]]:
    """Validates request payload and returns (status_code, response_dict)."""
    if not isinstance(payload, dict):
        return 400, {"error": "Request body must be a JSON object."}

    raw_text = payload.get("text")
    if not isinstance(raw_text, str):
        return 400, {"error": "Field 'text' must be a string."}

    text = raw_text.strip()
    if not text:
        return 400, {"error": "Please enter or upload article text to summarize."}

    original_words = len(text.split())
    if original_words > MAX_WORDS:
        return 400, {"error": f"Article exceeds the {MAX_WORDS:,}-word limit."}

    if not api_key:
        return 500, {
            "error": "GROQ_API_KEY is not configured on the server. Add it to .env locally or Vercel Environment Variables."
        }

    try:
        client = Groq(api_key=api_key)
        summary = summarize(client, text)
    except RuntimeError as err:
        return 502, {"error": str(err)}
    except Exception:
        return 500, {"error": "Unexpected error while generating summary."}

    summary_words, reduction = compute_stats(summary, original_words)
    return 200, {
        "summary": summary,
        "original_words": original_words,
        "summary_words": summary_words,
        "reduction": reduction,
    }


def send_bytes_response(req: BaseHTTPRequestHandler, status_code: int, content_type: str, data: bytes) -> None:
    """Writes a binary/text response with explicit Content-Type and Content-Length."""
    req.send_response(status_code)
    req.send_header("Content-Type", content_type)
    req.send_header("Content-Length", str(len(data)))
    req.end_headers()
    req.wfile.write(data)


def send_json_response(req: BaseHTTPRequestHandler, status_code: int, body: Dict[str, Any]) -> None:
    """Writes a UTF-8 JSON response with no-store caching headers."""
    encoded = json.dumps(body).encode("utf-8")
    req.send_response(status_code)
    req.send_header("Content-Type", "application/json; charset=utf-8")
    req.send_header("Content-Length", str(len(encoded)))
    req.send_header("Cache-Control", "no-store")
    req.end_headers()
    req.wfile.write(encoded)


class handler(BaseHTTPRequestHandler):
    """Vercel Python entrypoint serving static assets and /api/summarize."""

    def _route_path(self) -> str:
        return self.path.split("?", 1)[0]

    def do_GET(self) -> None:
        path = self._route_path()
        if path in ("/api/summarize", "/api/summarize/"):
            send_json_response(self, 200, {"status": "ok", "endpoint": "/api/summarize"})
            return

        static_entry = STATIC_FILES.get(path)
        if static_entry:
            filename, content_type = static_entry
            file_path = PUBLIC_DIR / filename
            if file_path.is_file():
                send_bytes_response(self, 200, content_type, file_path.read_bytes())
                return

        send_json_response(self, 404, {"error": "Not found."})

    def do_POST(self) -> None:
        if self._route_path() not in ("/api/summarize", "/api/summarize/"):
            send_json_response(self, 404, {"error": "Not found."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            send_json_response(self, 400, {"error": "Invalid Content-Length header."})
            return

        if content_length <= 0:
            send_json_response(self, 400, {"error": "Request body cannot be empty."})
            return

        if content_length > MAX_BODY_BYTES:
            send_json_response(self, 413, {"error": "Payload is too large (256 KB max)."})
            return

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            send_json_response(self, 400, {"error": "Request body must be valid UTF-8 JSON."})
            return

        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        status_code, result = process_summarization(payload, api_key)
        send_json_response(self, status_code, result)

