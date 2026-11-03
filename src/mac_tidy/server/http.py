"""HTTP transport: routing, request validation and security headers."""

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from ..config import ALLOWED_HOSTS, ALLOWED_ORIGINS, HOST, PORT, URL
from .static import static_file

MAX_BODY_BYTES = 4096
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'; object-src 'none'"
    ),
}
JSON = "application/json"


class Handler(BaseHTTPRequestHandler):
    server_version = "MacTidy"

    @property
    def app(self):
        return self.server.app

    @property
    def route_path(self):
        return urlparse(self.path).path

    def log_message(self, *args):
        pass

    def send(self, code, data, content_type=JSON):
        raw = json.dumps(data).encode() if content_type == JSON else data
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= MAX_BODY_BYTES:
            raise ValueError("Invalid request")
        body = json.loads(self.rfile.read(length))
        if not isinstance(body, dict):
            raise ValueError("Expected an object")
        return body

    def rejection(self):
        """Why a request must be refused, as ``(code, body)``, or None."""
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            return 403, {"code": "invalid_host", "error": "Localhost only"}
        if self.command != "POST":
            return None
        if self.headers.get("Origin") not in ALLOWED_ORIGINS:
            return 403, {"code": "invalid_origin", "error": f"Open this dashboard directly at {URL} and try again."}
        if not secrets.compare_digest(self.headers.get("X-Session-Token", ""), self.app.token):
            return 403, {"code": "session_expired", "error": "Your local session expired. Reconnecting…"}
        return None

    def do_GET(self):
        if rejected := self.rejection():
            return self.send(*rejected)
        routes = {
            "/api/status": self.app.status,
            "/api/report": self.app.get_report,
            "/api/cleanup": self.app.cleanup,
            "/api/insights": self.app.insights,
            "/api/space": self.app.space,
            "/api/trends": self.app.trends_summary,
            "/api/duplicates": self.app.duplicates_status,
            "/api/session": lambda: {"token": self.app.token},
        }
        if route := routes.get(self.route_path):
            return self.send(200, route())
        if found := static_file(self.route_path):
            file, content_type = found
            return self.send(200, file.read_bytes(), content_type)
        self.send(404, {"error": "Not found"})

    def do_POST(self):
        if rejected := self.rejection():
            return self.send(*rejected)
        routes = {
            "/api/rescan": self.app.rescan,
            "/api/duplicates/find": self.app.find_duplicates,
            "/api/duplicates/cancel": self.app.cancel_duplicates,
            "/api/duplicates/preview": self.app.preview_duplicate,
            "/api/reveal": self.app.reveal_item,
            "/api/trash/preview": self.app.preview_trash,
            "/api/trash/approve": self.app.approve_trash,
            "/api/activity/reveal": self.app.reveal_activity,
        }
        route = routes.get(self.route_path)
        if not route:
            return self.send(404, {"error": "Not found"})
        try:
            self.send(200, route(self.read_body()))
        except (ValueError, TypeError, OSError) as ex:
            self.send(400, {"error": str(ex)})


def make_server(app, host=HOST, port=PORT):
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.app = app
    return httpd
