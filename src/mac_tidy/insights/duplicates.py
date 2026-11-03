"""Explicit, bounded duplicate searches over local personal files.

Content is read only after start(). Equal sizes and edge samples make files
candidates; a full SHA-256 hash confirms a match. Excluded: changed, symlinked,
cloud-only, hard-linked and package files, dependency trees, and anything
inside a code project (projects keep intentional copies). No file is moved here.
"""

import hashlib
import os
import stat
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ..cleanup.fingerprint import fingerprint
from ..common.paths import local_regular, personal_path
from ..common.projects import project_root

MIN_FILE_BYTES = 1_000_000
CHUNK_BYTES = 1 << 20
EDGE_BYTES = 64 * 1024
MIN_BUDGET = 1_000_000
DEFAULT_BUDGET = 2_000_000_000
MAX_BUDGET = 32_000_000_000
MAX_FOLDER_ENTRIES = 10000
MAX_FOLDER_GROUPS = 100
MTIME_TOLERANCE = 0.00001

FILE_SCOPE = (
    "Indexed local personal files of at least 1 MB. Hard links, packages, dependency trees and "
    "files inside code projects excluded. APFS shared blocks may reduce actual savings."
)
FOLDER_SCOPE = (
    "Complete personal folders with matching measured sizes; maximum {groups} candidate groups and "
    "{entries:,} entries per folder. Folders inside code projects excluded. Full relative names and "
    "contents verified. Folder results are inspect-only."
)


class Skipped(Exception):
    """An item can't be verified (changed, vanished, unsupported)."""


class Cancelled(Exception):
    """The user cancelled the search."""


class Budget(Exception):
    """Reading this would exceed the read budget."""


@dataclass
class _Skips:
    budget: int = 0
    changed: int = 0
    project: int = 0


# Reading files

def _open(path):
    if str(Path(path).resolve(strict=True)) != str(Path(path).absolute()):
        raise Skipped("symlink")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    handle = os.fdopen(descriptor, "rb")
    if not local_regular(os.fstat(handle.fileno())):
        handle.close()
        raise Skipped("not a local regular file")
    return handle


def _identity(st):
    return (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_size)


def stable_hash(path, on_bytes=lambda count: None, cancel=lambda: False, max_bytes=None):
    """SHA-256 of a file, proving it did not change while it was read.

    Returns ``(hexdigest, fingerprint)``. Raises Budget before reading anything
    if the file is larger than ``max_bytes``.
    """
    with _open(path) as handle:
        before = os.fstat(handle.fileno())
        if max_bytes is not None and before.st_size > max_bytes:
            raise Budget()
        digest = hashlib.sha256()
        consumed = 0
        while consumed < before.st_size:
            if cancel():
                raise Cancelled()
            chunk = handle.read(min(CHUNK_BYTES, before.st_size - consumed))
            if not chunk:
                raise Skipped("truncated during hashing")
            digest.update(chunk)
            consumed += len(chunk)
            on_bytes(len(chunk))
        expected = _identity(before)
        if _identity(os.fstat(handle.fileno())) != expected or fingerprint(path) != list(expected):
            raise Skipped("changed during hashing")
        return digest.hexdigest(), list(expected)


def _quick_key(path, size):
    """A cheap fingerprint from a file's first and last bytes."""
    with _open(path) as handle:
        before = os.fstat(handle.fileno())
        head = handle.read(EDGE_BYTES)
        handle.seek(max(0, size - EDGE_BYTES))
        tail = handle.read(EDGE_BYTES)
        if before.st_size != size:
            raise Skipped("size changed")
        return hashlib.blake2b(head + tail, digest_size=16).digest()


def _group(items, key):
    """Groups of two or more items sharing a key. Unreadable items are dropped."""
    groups = {}
    for item in items:
        try:
            groups.setdefault(key(item), []).append(item)
        except (OSError, ValueError, Skipped):
            continue
    return [group for group in groups.values() if len(group) > 1]


class DuplicateFinder:
    """Runs one search at a time in a background thread."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._state = {"status": "idle", "groups": []}

    # State

    def status(self):
        with self._lock:
            return dict(self._state)

    def reset(self):
        with self._lock:
            if self._state["status"] != "running":
                self._state = {"status": "idle", "groups": []}

    def cancel(self):
        self._cancel.set()
        return {"cancelRequested": True}

    def mark_moved(self, path):
        """Drop a trashed copy from the results, and groups left with one copy."""
        with self._lock:
            if self._state.get("status") != "complete" or self._state.get("mode") != "files":
                return
            groups = []
            for group in self._state.get("groups", []):
                files = [f for f in group["files"] if f["path"] != path]
                if len(files) < 2:
                    continue
                groups.append({
                    **group,
                    "files": files,
                    "keeper": files[0]["index"],
                    "wasted": sum(f["logical"] for f in files[1:]),
                    "allocatedEstimate": sum(f["size"] for f in files[1:]),
                })
            self._state = {**self._state, "groups": groups, "wasted": sum(g["wasted"] for g in groups)}

    def _update(self, **fields):
        with self._lock:
            self._state.update(fields)

    def _progress(self, count):
        with self._lock:
            self._state["bytesHashed"] = self._state.get("bytesHashed", 0) + count

    def _bytes_hashed(self):
        return self.status().get("bytesHashed", 0)

    def _check_cancelled(self):
        if self._cancel.is_set():
            raise Cancelled()

    def _begin(self, revision, mode, budget):
        self._update(status="running", revision=revision, mode=mode, groups=[], bytesHashed=0,
                     budget=budget, skippedBudget=0, skippedChanged=0, skippedProject=0)

    def _finish(self, started, skips, **fields):
        self._update(status="complete", skippedBudget=skips.budget, skippedChanged=skips.changed,
                     skippedProject=skips.project, elapsed=round(time.time() - started), **fields)

    # Starting a search

    def start(self, files, revision, *, home, mode="files", report=None, budget=DEFAULT_BUDGET):
        """Begin a search in the background. Returns False if one is already running."""
        with self._lock:
            if self._state["status"] == "running":
                return False
            self._cancel.clear()
            self._state = {"status": "running", "revision": revision, "mode": mode, "groups": [],
                           "bytesHashed": 0, "budget": budget}
        target, args = (self._run_folders, (report, revision)) if mode == "folders" else (self._run, (files, revision))
        threading.Thread(target=target, args=args, kwargs={"home": home, "budget": budget}, daemon=True).start()
        return True

    def _guarded(self, started, search):
        """Run ``search`` and record how it ended: complete, cancelled or error."""
        try:
            search()
        except Cancelled:
            self._update(status="cancelled", groups=[], elapsed=round(time.time() - started))
        except Exception as ex:  # report failure instead of leaving the UI waiting
            self._update(status="error", groups=[], message=str(ex))

    # File search

    def _run(self, files, revision, *, home, budget=DEFAULT_BUDGET):
        started = time.time()
        self._begin(revision, "files", budget)
        self._guarded(started, lambda: self._search_files(files, home, budget, started))

    def _search_files(self, files, home, budget, started):
        skips = _Skips()
        candidates = self._collect_files(files, home, skips)
        groups = []
        for same_size in _group(candidates, lambda f: f["logical"]):
            self._check_cancelled()
            # Edge reads count toward the declared I/O budget too.
            edge_cost = sum(min(f["logical"], 2 * EDGE_BYTES) for f in same_size)
            if self._bytes_hashed() + edge_cost > budget:
                skips.budget += len(same_size)
                continue
            same_edges = _group(same_size, lambda f: _quick_key(f["path"], f["logical"]))
            self._progress(edge_cost)
            for edge_group in same_edges:
                if self._bytes_hashed() + sum(f["logical"] for f in edge_group) > budget:
                    skips.budget += len(edge_group)
                    continue
                groups.extend(self._confirm(edge_group, budget, skips))
        groups.sort(key=lambda g: g["wasted"], reverse=True)
        self._finish(started, skips, groups=groups, wasted=sum(g["wasted"] for g in groups),
                     filesChecked=len(candidates), scope=FILE_SCOPE)

    def _collect_files(self, files, home, skips):
        """Report rows that are still the same local regular file, each inode once."""
        candidates, seen, projects = [], set(), {}
        for row in files:
            self._check_cancelled()
            if row.get("logical", 0) < MIN_FILE_BYTES or not personal_path(row["path"], home):
                continue
            if project_root(row["path"], home, projects):
                skips.project += 1
                continue
            try:
                st = os.lstat(row["path"])
            except OSError:
                skips.changed += 1
                continue
            identity = (st.st_dev, st.st_ino)
            if not local_regular(st) or identity in seen or st.st_size != row["logical"]:
                continue
            if "mtime" in row and abs(st.st_mtime - row["mtime"]) > MTIME_TOLERANCE:
                continue
            if "mtimeNs" in row and st.st_mtime_ns != row["mtimeNs"]:
                continue
            seen.add(identity)
            candidates.append(row)
        return candidates

    def _confirm(self, edge_group, budget, skips):
        """Hash candidate files in full and return the groups that are truly identical."""
        by_hash = {}
        for row in edge_group:
            try:
                digest, fp = stable_hash(row["path"], self._progress, self._cancel.is_set,
                                         max_bytes=budget - self._bytes_hashed())
            except Budget:
                skips.budget += 1
            except (OSError, ValueError, Skipped):
                skips.changed += 1
            else:
                by_hash.setdefault(digest, []).append({**row, "fingerprint": fp})
        groups = []
        for digest, matches in by_hash.items():
            if len(matches) < 2:
                continue
            matches.sort(key=lambda f: (f.get("mtime", 0), f["path"]))
            groups.append({
                "id": digest,
                "sha256": digest,
                "size": matches[0]["logical"],
                "wasted": sum(f["logical"] for f in matches[1:]),
                "allocatedEstimate": sum(f["size"] for f in matches[1:]),
                "files": matches,
                "keeper": matches[0]["index"],
            })
        return groups

    # Folder search

    def _list_folder(self, path, entries_so_far):
        """Entries of one folder, sorted by name, within the folder entry limit."""
        children = []
        with os.scandir(path) as scan:
            for child in scan:
                self._check_cancelled()
                if len(children) >= MAX_FOLDER_ENTRIES - entries_so_far:
                    raise Skipped("folder entry limit")
                children.append(child)
        return sorted(children, key=lambda entry: entry.name)

    def _folder_manifest(self, path, home, budget):
        """A digest of a folder's relative names and file contents.

        Returns ``(digest, bytes_read, allocated_bytes)``. Raises Skipped for a
        folder with symlinks, excluded or unsupported entries, or that changed.
        """
        digest = hashlib.sha256()
        entries = read = allocated = 0
        folders = [Path(path)]
        verified = []  # (path, fingerprint) re-checked at the end
        while folders:
            folder = folders.pop()
            if not personal_path(str(folder), home):
                raise Skipped("excluded directory")
            verified.append((str(folder), fingerprint(str(folder))))
            for child in self._list_folder(folder, entries):
                self._check_cancelled()
                entries += 1
                if entries > MAX_FOLDER_ENTRIES:
                    raise Skipped("folder entry limit")
                if child.is_symlink() or not personal_path(child.path, home):
                    raise Skipped("folder contains excluded entries")
                relative = str(Path(child.path).relative_to(path))
                st = child.stat(follow_symlinks=False)
                if stat.S_ISDIR(st.st_mode):
                    digest.update(b"D\0" + relative.encode() + b"\0")
                    folders.append(Path(child.path))
                elif local_regular(st):
                    remaining = min(budget - read, self.status()["budget"] - self._bytes_hashed())
                    if st.st_size > remaining:
                        raise Budget()
                    value, fp = stable_hash(child.path, self._progress, self._cancel.is_set, max_bytes=remaining)
                    read += st.st_size
                    allocated += st.st_blocks * 512
                    digest.update(b"F\0" + relative.encode() + b"\0" + str(st.st_size).encode()
                                  + b"\0" + value.encode() + b"\0")
                    verified.append((child.path, fp))
                else:
                    raise Skipped("unsupported or nonlocal entry")
        for item, fp in verified:
            if fingerprint(item) != fp:
                raise Skipped("folder changed")
        return digest.hexdigest(), read, allocated

    def _run_folders(self, report, revision, *, home, budget=DEFAULT_BUDGET, min_bytes=MIN_FILE_BYTES):
        started = time.time()
        self._begin(revision, "folders", budget)
        self._guarded(started, lambda: self._search_folders(report, home, budget, min_bytes, started))

    def _search_folders(self, report, home, budget, min_bytes, started):
        skips = _Skips()
        projects = {}
        candidates = []
        for d in report["dirs"]:
            if d.get("partial") or d.get("logical", d["size"]) < min_bytes or not personal_path(d["path"], home):
                continue
            if project_root(d["path"], home, projects):
                skips.project += 1
                continue
            candidates.append(d)
        def size_of(d):
            return d.get("logical", d["size"])

        size_groups = sorted(_group(candidates, size_of), key=lambda g: size_of(g[0]), reverse=True)[:MAX_FOLDER_GROUPS]

        verified = []
        for group in size_groups:
            matches = {}
            for d in group:
                self._check_cancelled()
                if self._bytes_hashed() + size_of(d) > budget:
                    skips.budget += 1
                    continue
                try:
                    digest, _, allocated = self._folder_manifest(d["path"], home, budget - self._bytes_hashed())
                except Budget:
                    skips.budget += 1
                except (OSError, ValueError, Skipped):
                    skips.changed += 1
                else:
                    matches.setdefault(digest, []).append({**d, "allocatedEstimate": allocated})
            for digest, folders in matches.items():
                if len(folders) > 1:
                    folders.sort(key=lambda d: d["path"])
                    verified.append({"id": digest, "size": size_of(folders[0]), "folders": folders})

        # Hide groups wholly inside an already listed group. Partial overlaps can
        # remain, so folder matches deliberately carry no combined savings figure.
        verified.sort(key=lambda g: g["size"], reverse=True)
        groups, covered = [], []
        for group in verified:
            if all(any(d["path"].startswith(parent + "/") for parent in covered) for d in group["folders"]):
                continue
            groups.append(group)
            covered.extend(d["path"] for d in group["folders"])
        self._finish(started, skips, groups=groups, wasted=None,
                     foldersChecked=sum(len(g) for g in size_groups),
                     scope=FOLDER_SCOPE.format(groups=MAX_FOLDER_GROUPS, entries=MAX_FOLDER_ENTRIES))
