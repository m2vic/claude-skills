from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


def make_server(host: str, port: int, on_payment_webhook: Callable[[bytes, str], int]) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            status = 404
            if self.path == "/webhooks/payments":
                # Read raw bytes: the signature covers the exact body, not re-encoded JSON.
                raw_body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                try:
                    status = on_payment_webhook(raw_body, self.headers.get("X-Provider-Signature", ""))
                except Exception:
                    status = 500
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer((host, port), Handler)
