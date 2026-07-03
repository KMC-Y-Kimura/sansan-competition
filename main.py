from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve the Google Classroom support GUI prototype."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(PUBLIC_DIR),
    )

    with ReusableTCPServer((args.host, args.port), handler) as server:
        url = f"http://{args.host}:{args.port}"
        print(f"Serving sansan-competition GUI at {url}")
        server.serve_forever()


if __name__ == "__main__":
    main()
