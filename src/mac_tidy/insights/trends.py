"""Storage over time: a capacity point per scan, plus what grew between the last two."""

import threading

from ..common.jsonfile import read_json, write_json_atomic

MAX_POINTS = 60
MIN_CHANGE_BYTES = 200_000_000
MAX_CHANGES = 15
# A folder is hidden when one descendant explains most of its change.
EXPLAINED_SHARE = 0.8
BASELINE_KEYS = ("dirs", "partial", "scope")
CAPACITY_KEYS = ("finished", "used", "free", "total")
COVERAGE_NOTE = (
    "Folder changes compare complete locations present in both scans. Newly indexed, missing or "
    "partially readable folders are not claimed as exact growth."
)


def snapshot(report):
    """A point in time: capacity, and a folder-size map for comparing against later scans."""
    return {
        "finished": report["finished"],
        **{key: report["disk"][key] for key in ("used", "free", "total")},
        "dirs": {d["path"]: d["size"] for d in report["dirs"]},
        "partial": [d["path"] for d in report["dirs"] if d.get("partial")],
        "scope": sorted(root["path"] for root in report.get("roots", [])),
    }


def _changes(before, after):
    """Folders whose size changed most, keeping the most specific folder.

    Only folders fully readable in both scans are compared, and only when both
    scans covered the same roots.
    """
    if before.get("scope") != after.get("scope"):
        return []
    unreliable = set(before.get("partial", [])) | set(after.get("partial", []))
    changed = {}
    for path in before["dirs"].keys() & after["dirs"].keys():
        delta = after["dirs"][path] - before["dirs"][path]
        if path not in unreliable and abs(delta) >= MIN_CHANGE_BYTES:
            changed[path] = delta

    def explained_by_descendant(path, delta):
        return any(
            other.startswith(path + "/")
            and abs(other_delta) >= EXPLAINED_SHARE * abs(delta)
            and (other_delta > 0) == (delta > 0)
            for other, other_delta in changed.items()
        )

    result = [
        {"path": path, "before": before["dirs"][path], "after": after["dirs"][path], "delta": delta}
        for path, delta in changed.items()
        if not explained_by_descendant(path, delta)
    ]
    return sorted(result, key=lambda change: abs(change["delta"]), reverse=True)[:MAX_CHANGES]


class TrendLog:
    """Keeps up to 60 capacity points and full folder maps only for the last two scans."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self.save_warning = None
        try:
            self._points = read_json(path)
        except (OSError, ValueError):
            self._points = []

    def record(self, report):
        """Add a point for this report. Returns False if it was already recorded."""
        with self._lock:
            if any(point["finished"] == report["finished"] for point in self._points):
                return False
            self._points.append(snapshot(report))
            self._points.sort(key=lambda point: point["finished"])
            self._points = self._points[-MAX_POINTS:]
            for point in self._points[:-2]:
                for key in BASELINE_KEYS:
                    point.pop(key, None)
            try:
                write_json_atomic(self.path, self._points)
                self.save_warning = None
            except OSError:
                self.save_warning = "History could not be saved to disk."
            return True

    def summary(self):
        with self._lock:
            points = list(self._points)
        previous, latest = (points[-2], points[-1]) if len(points) > 1 else (None, None)
        comparable = previous is not None and "dirs" in previous and previous.get("scope") == latest.get("scope")
        return {
            "points": [{key: point[key] for key in CAPACITY_KEYS} for point in points],
            "changes": _changes(previous, latest) if comparable else [],
            "since": previous["finished"] if previous else None,
            "comparable": comparable,
            "coverageNote": COVERAGE_NOTE,
            "saveWarning": self.save_warning,
        }
