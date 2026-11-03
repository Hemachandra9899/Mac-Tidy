"""The persistent log of completed moves to Trash."""

import os
import secrets
import threading
import time
from pathlib import Path

from ..common.jsonfile import read_json, write_json_atomic

STATUS_LABELS = {
    "in_trash": "In Trash",
    "not_in_trash": "No longer in Trash",
    "unknown": "Trash status unavailable",
}


def _trash_status(trash_path):
    try:
        os.lstat(trash_path)
        return "in_trash"
    except FileNotFoundError:
        return "not_in_trash"
    except OSError:
        return "unknown"


class ActivityLog:
    """Thread-safe, append-only record of moves, saved as JSON."""

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._entries = self._load()

    def _load(self):
        try:
            return read_json(self.path)
        except FileNotFoundError:
            return []
        except (OSError, ValueError):
            # Keep the unreadable log for inspection rather than overwriting it.
            try:
                self.path.replace(self.path.with_suffix(".corrupt.json"))
            except OSError:
                pass
            return []

    def __len__(self):
        return len(self._entries)

    def entries(self):
        with self._lock:
            return [dict(entry) for entry in self._entries]

    def record(self, path, trash_path, size):
        """Append a completed move. A save failure is reported, never raised:
        the item is already in Trash and must not look like a failed move."""
        entry = {
            "id": secrets.token_hex(12),
            "path": path,
            "trashPath": trash_path,
            "size": size,
            "time": time.time(),
            "status": "trashed",
        }
        with self._lock:
            self._entries.append(entry)
            try:
                write_json_atomic(self.path, self._entries)
            except OSError:
                return {**entry, "warning": "Moved to Trash; activity log could not be saved."}
        return dict(entry)

    def find(self, entry_id):
        with self._lock:
            return next((dict(e) for e in self._entries if e["id"] == entry_id), None)

    def with_status(self):
        """Entries annotated with whether each item is still in Trash. Not persisted."""
        entries = self.entries()
        for entry in entries:
            entry["status"] = _trash_status(entry["trashPath"])
            entry["statusLabel"] = STATUS_LABELS[entry["status"]]
        return entries

    def moved_since(self, path, since):
        """True if ``path`` or one of its ancestors was moved after ``since``."""
        return any(
            e["time"] > since and (path == e["path"] or path.startswith(e["path"] + "/"))
            for e in self.entries()
        )
