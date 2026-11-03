"""Which scanned items may be offered for Move to Trash.

The policy is an allowlist. It is recomputed from the path on every check, so a
category sent by the browser never grants permission.
"""

from pathlib import Path

from ..config import HOME
from .classify import classify

MANAGED_REASON = "This location is managed by macOS or its owning app. Review it there."
PROTECTED_NAMES = {".git", ".ssh", ".aws", ".gnupg", ".trash"}
APPLE_MANAGED_NAMES = {"GeoServices", "CloudKit", "FamilyCircle", "familycircled"}
PERSONAL_FOLDERS = {"Downloads", "Documents", "Desktop"}

# Removing a single file from inside one of these packages corrupts the whole
# app or library, so only the package itself may ever be considered.
PACKAGE_SUFFIXES = (
    ".app",
    ".bundle",
    ".framework",
    ".photoslibrary",
    ".musiclibrary",
    ".tvlibrary",
    ".fcpbundle",
    ".logicx",
    ".band",
    ".xcarchive",
)


def _result(allowed, reason):
    return {"allowed": allowed, "reason": reason}


def _is_eligible_cache(path):
    padded = path + "/"
    return (
        "/node_modules/.cache/webpack/" in padded
        or "/Library/Caches/" in path
        or "/.npm/_cacache/" in padded
        or "/.cache/pip/" in padded
        or "/.cache/uv/" in padded
    )


def action_policy(row, item_type, home=HOME):
    """Return {'allowed': bool, 'reason': str} for moving ``row`` to Trash."""
    path = Path(row["path"])
    try:
        parts = path.relative_to(Path(home)).parts
    except ValueError:
        return _result(False, MANAGED_REASON)

    if len(parts) < 2 or any(part.lower() in PROTECTED_NAMES for part in parts):
        return _result(
            False, "Home folders, credentials, source-control data and Trash are protected."
        )
    if parts[0] == "Library" and len(parts) < 3:
        return _result(
            False,
            "Review individual app caches inside this folder. The entire Library or "
            "Caches folder cannot be trashed here.",
        )
    if any(
        part.startswith(("com.apple.", "group.com.apple.")) or part in APPLE_MANAGED_NAMES
        for part in parts
    ):
        return _result(False, MANAGED_REASON)
    if any(part.lower().endswith(PACKAGE_SUFFIXES) for part in parts[:-1]):
        return _result(
            False, "This item is inside an app or library package. Manage the package as a whole."
        )

    text = str(path)
    kind = classify(text, home)["kind"]
    if kind == "cache" and _is_eligible_cache(text):
        return _result(True, "Rebuildable cache. Stop its app, renders and build jobs first. It may regenerate.")
    if kind == "logs" and "/Library/Logs/" in text:
        return _result(True, "Review old logs. Keep logs needed for debugging, then quit the owning app.")
    if (
        item_type == "file"
        and parts[0] in PERSONAL_FOLDERS
        and not any(part.startswith(".") for part in parts)
    ):
        return _result(True, "Personal file. Approve only if you no longer need it or have another copy.")
    return _result(False, MANAGED_REASON)
