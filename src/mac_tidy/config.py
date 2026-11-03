"""Paths and network settings shared across Mac Tidy."""

import os
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"
ALLOWED_HOSTS = frozenset({f"127.0.0.1:{PORT}", f"localhost:{PORT}"})
ALLOWED_ORIGINS = frozenset(f"http://{host}" for host in ALLOWED_HOSTS)

HOME = str(Path.home())
PACKAGE_DIR = Path(__file__).resolve().parent
WEB_DIR = PACKAGE_DIR / "web"
HELPER_PATH = PACKAGE_DIR / "bin" / "mac-tidy-helper"

# Scan results and the activity log live outside the source tree.
# MAC_TIDY_DATA_DIR lets tests run against an isolated location.
DATA_DIR = Path(
    os.environ.get("MAC_TIDY_DATA_DIR")
    or Path.home() / "Library" / "Application Support" / "Mac Tidy"
)
