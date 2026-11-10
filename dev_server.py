#!/usr/bin/env python3
"""Local development server serving public/ static files and /api/summarize."""

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from api.summarize import handler as summarize_handler

ROOT_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT_DIR / "public"


class LocalDevServer(ThreadingHTTPServer):
    allow_reuse_address = True


class LocalDevHandler(SimpleHTTPRequestHandler):
    """Routes /api/summarize to the Vercel handler and serves static files from public/."""

    def _route_path(self) -> str:
        return self.path.split("?", 1)[0]

    def do_GET(self) -> None:
        if self._route_path() == "/api/summarize":
            summarize_handler.do_GET(self)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self._route_path() == "/api/summarize":
            summarize_handler.do_POST(self)
            return
        self.send_error(404, "Endpoint not found")


def main() -> None:
    port = int(os.environ.get("PORT", "3000"))
    request_handler = partial(LocalDevHandler, directory=str(PUBLIC_DIR))
    server = LocalDevServer(("127.0.0.1", port), request_handler)
    print(f"Serving Article Summarizer at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
