"""Command-line entry point: start the server and open the dashboard."""

import argparse
import json
import signal
import subprocess
import sys
import urllib.error
import urllib.request

from .config import HELPER_PATH, PACKAGE_DIR, PORT, URL
from .server import App, make_server


def running_instance():
    """Status of a Mac Tidy server already on the port, or None."""
    try:
        with urllib.request.urlopen(URL + "/api/status", timeout=1) as response:
            return json.load(response)
    except (urllib.error.URLError, OSError, ValueError):
        return None


def open_dashboard():
    subprocess.run(["/usr/bin/open", URL + "/#overview"], check=False)


def _raise_interrupt(*_):
    raise KeyboardInterrupt


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mac-tidy", description="Review-first storage cleaner for macOS.")
    parser.add_argument("--no-open", action="store_true", help="start the server without opening a browser")
    parser.add_argument("--check", action="store_true", help="print installation status as JSON and exit")
    args = parser.parse_args(argv)

    status = running_instance()
    if args.check:
        print(json.dumps({
            "package": str(PACKAGE_DIR),
            "nativeHelper": HELPER_PATH.is_file(),
            "runningProject": status.get("projectPath") if status else None,
        }))
        return 0

    if status:
        if status.get("projectPath") != str(PACKAGE_DIR):
            sys.exit(f"Another Mac Tidy copy is using port {PORT}. Stop it first, then try again.")
        print("Mac Tidy is already running.")
        if not args.no_open:
            open_dashboard()
        return 0

    if not HELPER_PATH.is_file():
        sys.exit("The native helper is missing. Build it with `make helper`.")

    app = App()
    try:
        httpd = make_server(app)
    except OSError as ex:
        sys.exit(f"Could not listen on port {PORT}: {ex.strerror}. Is another app using it?")
    if not app.load_saved_report():
        app.start_scan()

    signal.signal(signal.SIGTERM, _raise_interrupt)
    print(f"Mac Tidy is running at {URL}. Press Control-C to stop.", flush=True)
    if not args.no_open:
        open_dashboard()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Mac Tidy…", flush=True)
    finally:
        httpd.server_close()
        app.wait_for_actions()
    return 0


if __name__ == "__main__":
    sys.exit(main())
