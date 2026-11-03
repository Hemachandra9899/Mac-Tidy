"""Serve the dashboard's own files, and nothing else."""

from ..config import WEB_DIR

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


def static_file(url_path):
    """Resolve a URL path to ``(file, content_type)`` inside WEB_DIR, or None."""
    relative = "index.html" if url_path == "/" else url_path.lstrip("/")
    if any(part.startswith(".") for part in relative.split("/")):
        return None
    candidate = (WEB_DIR / relative).resolve()
    content_type = CONTENT_TYPES.get(candidate.suffix)
    if not content_type or not candidate.is_relative_to(WEB_DIR) or not candidate.is_file():
        return None
    return candidate, content_type
