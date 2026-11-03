"""Metadata-only storage scan.

Never reads file contents, never follows symlinks, stays on each root's
volume and counts hard-linked files once. Sizes are allocated bytes
(st_blocks * 512).
"""

import datetime
import heapq
import os
import shutil
import time

from ..config import HOME
from ..common.paths import personal_path, local_regular

ROOTS = [HOME, "/Users/Shared", "/Applications", "/Library", "/private/var", "/opt", "/usr/local"]
MAX_LARGEST_FILES = 1500
MAX_REVIEW_FILES = 10000
MIN_REVIEW_BYTES = 1_000_000
MAX_ERRORS = 1000
PROGRESS_INTERVAL_SECONDS = 1
SNAPSHOT_NOTE = (
    "Snapshot sizes are not included in this metadata scan. Use macOS Storage "
    "settings or Time Machine to review snapshot management."
)


def data_volume():
    return "/System/Volumes/Data" if os.path.exists("/System/Volumes/Data") else "/"


class _Scan:
    def __init__(self, progress):
        self.progress = progress
        self.dirs = []
        self.files = []  # min-heap of (size, sequence, row)
        self.review_files = []
        self.review_count = 0
        self.seen_links = set()
        self.errors = []
        self.error_count = 0
        self.file_count = 0
        self.started = time.time()
        self.last_progress = 0

    def error(self, path, ex):
        self.error_count += 1
        if len(self.errors) < MAX_ERRORS:
            self.errors.append({"path": path, "reason": str(ex)})

    def add_file(self, entry, st, parent):
        if st.st_nlink > 1:
            key = (st.st_dev, st.st_ino)
            if key in self.seen_links:
                return 0
            self.seen_links.add(key)
        size = st.st_blocks * 512
        self.file_count += 1
        row = {
            "path": entry.path,
            "name": entry.name,
            "parent": parent,
            "size": size,
            "logical": st.st_size,
            "mtime": st.st_mtime,
            "mtimeNs": st.st_mtime_ns,
            "device": st.st_dev, "inode": st.st_ino,
        }
        if size >= MIN_REVIEW_BYTES and personal_path(entry.path, HOME) and local_regular(st):
            self.review_count += 1
            review = (size, self.file_count, dict(row))
            if len(self.review_files) < MAX_REVIEW_FILES:heapq.heappush(self.review_files, review)
            elif size > self.review_files[0][0]:heapq.heapreplace(self.review_files, review)
        item = (size, self.file_count, row)
        if len(self.files) < MAX_LARGEST_FILES:
            heapq.heappush(self.files, item)
        elif size > self.files[0][0]:
            heapq.heapreplace(self.files, item)
        return size

    def open_dir(self, path, parent, device):
        """Record a directory and its files. Returns (row, subdirectory paths) or None."""
        try:
            st = os.lstat(path)
        except OSError as ex:
            self.error(path, ex)
            if parent is not None:
                self.dirs[parent]["partial"] = True
            return None
        if os.path.islink(path) or st.st_dev != device:
            return None

        row = {
            "id": len(self.dirs),
            "path": path,
            "name": os.path.basename(path) or path,
            "parent": parent,
            "size": 0,
            "partial": False,
            "mtime": st.st_mtime,
            "latestMtime": st.st_mtime, "logical": 0,
        }
        self.dirs.append(row)
        subdirs = []
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        est = entry.stat(follow_symlinks=False)
                        if est.st_dev != device:
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            subdirs.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            row["size"] += self.add_file(entry, est, row["id"])
                            row["logical"] += est.st_size
                            row["latestMtime"] = max(row["latestMtime"], est.st_mtime)
                    except OSError as ex:
                        row["partial"] = True
                        self.error(entry.path, ex)
        except OSError as ex:
            row["partial"] = True
            self.error(path, ex)
        return row, iter(subdirs)

    def walk(self, root):
        """Iterative depth-first walk; deep trees cannot exhaust the call stack."""
        try:
            device = os.stat(root).st_dev
        except OSError as ex:
            self.error(root, ex)
            return
        opened = self.open_dir(root, None, device)
        if not opened:
            return
        stack = [opened]
        while stack:
            row, children = stack[-1]
            child = next(children, None)
            if child is not None:
                opened = self.open_dir(child, row["id"], device)
                if opened:
                    stack.append(opened)
                continue
            stack.pop()
            if stack:
                stack[-1][0]["size"] += row["size"]
                stack[-1][0]["logical"] += row["logical"]
                stack[-1][0]["latestMtime"] = max(stack[-1][0]["latestMtime"], row["latestMtime"])
            self.report_progress(row["path"])

    def report_progress(self, current):
        if self.progress and time.time() - self.last_progress > PROGRESS_INTERVAL_SECONDS:
            self.last_progress = time.time()
            self.progress(
                {
                    "status": "scanning",
                    "current": current,
                    "filesScanned": self.file_count,
                    "dirsScanned": len(self.dirs),
                    "errorsCount": self.error_count,
                    "elapsed": round(time.time() - self.started),
                }
            )


def scan_tree(roots, progress=None):
    """Scan ``roots`` and return a full report dictionary."""
    scan = _Scan(progress)
    root_rows = []
    for root in roots:
        if not os.path.lexists(root):
            continue
        first = len(scan.dirs)
        scan.walk(root)
        if len(scan.dirs) > first:
            root_rows.append(scan.dirs[first])

    # Incomplete coverage of any folder makes every ancestor a lower bound too.
    for row in reversed(scan.dirs):
        if row["partial"] and row["parent"] is not None:
            scan.dirs[row["parent"]]["partial"] = True

    disk = shutil.disk_usage(data_volume())
    return {
        "status": "complete",
        "started": datetime.datetime.fromtimestamp(scan.started).astimezone().isoformat(),
        "finished": datetime.datetime.now().astimezone().isoformat(),
        "elapsed": round(time.time() - scan.started),
        "roots": root_rows,
        "dirs": scan.dirs,
        "files": [item[2] for item in sorted(scan.files, reverse=True)],
        "reviewFiles": [item[2] for item in sorted(scan.review_files, reverse=True)],
        "reviewFilesEligible": scan.review_count,
        "reviewFilesLimit": MAX_REVIEW_FILES,
        "filesScanned": scan.file_count,
        "dirsScanned": len(scan.dirs),
        "errors": scan.errors,
        "errorsCount": scan.error_count,
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "home": HOME,
        "snapshots": SNAPSHOT_NOTE,
    }
