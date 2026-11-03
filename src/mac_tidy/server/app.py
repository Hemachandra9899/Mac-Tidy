"""Application state and use cases behind the HTTP API."""

import datetime
import os
import secrets
import shutil
import threading
from pathlib import Path

from .. import __version__
from ..cleanup import ActivityLog, TrashManager, native
from ..common.jsonfile import read_json, write_json_atomic
from ..config import DATA_DIR, HOME, PACKAGE_DIR
from ..scan import ROOTS, data_volume, prepare_report, recommendations, scan_tree

SCANNING_STATE = {
    "status": "scanning",
    "current": "Preparing scan…",
    "filesScanned": 0,
    "dirsScanned": 0,
    "errorsCount": 0,
    "elapsed": 0,
}


class App:
    """Scan state, the current report and Trash actions.

    ``lock`` guards ``state`` and ``report`` and is held only briefly.
    ``action_lock`` serialises starting a scan and running a Trash move, so a
    scan can never replace the report while an approved move is running.
    """

    def __init__(self, data_dir=DATA_DIR, mover=native.move_to_trash, revealer=native.reveal, roots=ROOTS, home=HOME):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.report_file = self.data_dir / "report.json"
        self.roots = roots
        self.reveal = revealer
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.action_lock = threading.Lock()
        self.state = {"status": "starting"}
        self.report = None
        self.activity = ActivityLog(self.data_dir / "activity.json")
        self.trash = TrashManager(self.activity, mover, home=home)

    # Report lifecycle

    def _set_report(self, report):
        with self.lock:
            self.report = report
            self.state = {"status": "complete"}

    def _set_state(self, state):
        with self.lock:
            self.state = state

    def load_saved_report(self):
        try:
            self._set_report(prepare_report(read_json(self.report_file)))
        except (OSError, ValueError, KeyError):
            return False
        return True

    def start_scan(self):
        with self.action_lock, self.lock:
            if self.state["status"] == "scanning":
                return False
            self.state = dict(SCANNING_STATE)
        threading.Thread(target=self._scan, daemon=True).start()
        return True

    def _scan(self):
        try:
            report = prepare_report(scan_tree(self.roots, self._set_state))
            write_json_atomic(self.report_file, report)
            self._set_report(report)
        except Exception as ex:  # surface any failure to the UI instead of a stuck spinner
            self._set_state({"status": "error", "message": str(ex)})

    def _require_report(self):
        """The current report's revision. Caller holds ``lock``."""
        if self.state["status"] == "scanning" or not self.report:
            raise ValueError("Wait for the scan to finish.")
        return self.report["finished"]

    def was_moved(self, path):
        """True if ``path`` or an ancestor was moved to Trash since the last scan."""
        since = datetime.datetime.fromisoformat(self.report["finished"]).timestamp() if self.report else 0
        return self.activity.moved_since(path, since)

    # Read endpoints

    def status(self):
        with self.lock:
            return {
                **self.state,
                "version": __version__,
                "hasReport": self.report is not None,
                "reportFinished": self.report["finished"] if self.report else None,
                "activityCount": len(self.activity),
                "projectPath": str(PACKAGE_DIR),
                "pid": os.getpid(),
            }

    def get_report(self):
        with self.lock:
            return self.report or {"status": "scanning"}

    def cleanup(self):
        history = self.activity.with_status()
        with self.lock:
            cards = recommendations(self.report, self.was_moved)
        return {
            "cards": cards,
            "history": list(reversed(history)),
            "diskFree": shutil.disk_usage(data_volume()).free,
            "bytesInTrash": sum(h["size"] for h in history if h["status"] == "in_trash"),
            "unverifiedTrashCount": sum(h["status"] == "unknown" for h in history),
        }

    # Actions

    def _resolve_row(self, body):
        """Map a browser selection back to a scanned row and confirm it still matches."""
        if not self.report:
            raise ValueError("Wait for the scan to finish.")
        if body.get("type") not in ("dir", "file"):
            raise ValueError("Invalid item type")
        rows = self.report["dirs"] if body["type"] == "dir" else self.report["files"]
        index = body.get("id")
        if type(index) is not int or not 0 <= index < len(rows):
            raise ValueError("Invalid scanned item")
        row = rows[index]
        if body.get("path") != row["path"]:
            raise ValueError("The scan changed. Select the item again.")
        if not os.path.lexists(row["path"]):
            raise ValueError("Item no longer exists. Rescan to refresh.")
        return row

    def rescan(self, _body):
        return {"started": self.start_scan()}

    def reveal_item(self, body):
        with self.lock:
            row = self._resolve_row(body)
        self.reveal(row["path"])
        return {"ok": True}

    def preview_trash(self, body):
        with self.action_lock, self.lock:
            revision = self._require_report()
            row = self._resolve_row(body)
            if self.was_moved(row["path"]):
                raise ValueError("This location was already moved. Rescan before reviewing a recreated cache.")
            return self.trash.preview(row, body["type"], revision)

    def approve_trash(self, body):
        if body.get("confirmed") is not True:
            raise ValueError("Confirm this exact item before moving it to Trash.")
        # Keep action_lock for the whole move so no scan starts meanwhile, but
        # release ``lock`` so status polling stays responsive.
        with self.action_lock:
            with self.lock:
                revision = self._require_report()
            item = self.trash.execute(body.get("approval", ""), revision)
        return {"ok": True, "item": item}

    def reveal_activity(self, body):
        entry = self.activity.find(body.get("id"))
        if not entry:
            raise ValueError("Activity item not found")
        self.reveal(entry["trashPath"])
        return {"ok": True}

    def wait_for_actions(self):
        """Block until an in-flight Trash move has been recorded."""
        with self.action_lock:
            pass
