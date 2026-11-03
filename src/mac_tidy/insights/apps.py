"""Per-app storage: each app's bundle plus its data spread across ~/Library,
and large folders no installed app claims (possibly left by a removed app)."""

import plistlib
import re
from pathlib import Path

from ..rules.policy import APPLE_MANAGED_NAMES
from .developer import TOOLS

APP_FOLDERS = ("/Applications", "~/Applications")
LIBRARY_LOCATIONS = {
    "Application Support": "Support files",
    "Caches": "Caches",
    "Containers": "Sandboxed data",
    "Group Containers": "Shared data",
    "Logs": "Logs",
    "HTTPStorages": "Web storage",
    "WebKit": "Web storage",
    "Saved Application State": "Window state",
}
MIN_UNMATCHED_BYTES = 50_000_000
MIN_VENDOR_LENGTH = 4
NAME_SEPARATORS = "-_. "
TEAM_PREFIX = re.compile(r"^(group\.|[A-Z0-9]{10}\.)")
# Folders owned by command-line tools, which the Developer view covers.
TOOL_FOLDERS = {Path(tool.path).name.lower() for tool in TOOLS} | {"ms-playwright", "node-gyp", "typescript"}


def _clean(name):
    return "".join(ch for ch in name if ch.isprintable()).strip()


def _is_apple(folder_name):
    return folder_name.startswith(("com.apple.", "group.com.apple.")) or folder_name in APPLE_MANAGED_NAMES


def _vendor(bundle_id):
    """'com.google.Chrome' -> 'google'."""
    parts = bundle_id.lower().split(".")
    return parts[1] if len(parts) > 2 else ""


def installed_apps(folders=APP_FOLDERS):
    """``{bundle_id: name}`` for apps in the Applications folders. Reads Info.plist only."""
    apps = {}
    for folder in folders:
        for bundle in Path(folder).expanduser().glob("*.app"):
            try:
                with open(bundle / "Contents" / "Info.plist", "rb") as f:
                    info = plistlib.load(f)
            except (OSError, plistlib.InvalidFileException, ValueError):
                continue
            bundle_id = info.get("CFBundleIdentifier")
            if bundle_id:
                name = info.get("CFBundleDisplayName") or info.get("CFBundleName") or bundle.stem
                apps[bundle_id] = {"name": _clean(name), "path": str(bundle)}
    return apps


class _Matcher:
    """Decides which installed app owns a Library folder."""

    def __init__(self, apps):
        self.apps = apps
        self.names = {}
        for bundle_id, info in apps.items():
            if len(info["name"]) >= MIN_VENDOR_LENGTH:
                self.names.setdefault(info["name"].lower(), []).append(bundle_id)
        self.vendors = {}
        for bundle_id in apps:
            vendor = _vendor(bundle_id)
            if len(vendor) >= MIN_VENDOR_LENGTH:
                self.vendors.setdefault(vendor, []).append(bundle_id)

    def owner(self, folder_name):
        """``(bundle_id, [])`` when one app clearly owns the folder, otherwise
        ``(None, candidate_bundle_ids)``. Tries exact bundle id, a sub-identifier,
        the app's name as a prefix, then the vendor ('Google' -> com.google.*)."""
        key = TEAM_PREFIX.sub("", folder_name.removesuffix(".savedState"))
        if key in self.apps:
            return key, []
        identifiers = [bundle_id for bundle_id in self.apps if key.startswith(bundle_id + ".")]
        if identifiers:
            return max(identifiers, key=len), []
        lower = key.lower()
        names = [name for name in self.names if lower == name or (lower.startswith(name) and lower[len(name)] in NAME_SEPARATORS)]
        if names:
            candidates = self.names[max(names, key=len)]
            return (candidates[0], []) if len(candidates) == 1 else (None, candidates)
        candidates = self._vendor_candidates(key)
        return (candidates[0], []) if len(candidates) == 1 else (None, candidates)

    def _vendor_candidates(self, key):
        """Apps by the same vendor as a folder. A reverse-DNS folder
        ('com.brave.Browser.x') must name the vendor exactly; a plain folder
        ('BraveSoftware') only has to begin with it."""
        vendor = _vendor(key)
        if vendor:
            return self.vendors.get(vendor, [])
        lower = key.lower()
        return [bundle_id for prefix, ids in self.vendors.items() if lower.startswith(prefix) for bundle_id in ids]


def app_breakdown(report, apps):
    home = report["home"]
    dirs = report["dirs"]
    by_path = {d["path"]: d for d in dirs}
    matcher = _Matcher(apps)
    totals = {
        bundle_id: {"bundleId": bundle_id, "name": info["name"], "appPath": info["path"],
                    "appBytes": by_path.get(info["path"], {}).get("size", 0), "dataBytes": 0, "locations": []}
        for bundle_id, info in apps.items()
    }
    unmatched = []

    for location, label in LIBRARY_LOCATIONS.items():
        base = by_path.get(f"{home}/Library/{location}")
        if not base:
            continue
        for d in dirs:
            if d["parent"] != base["id"] or _is_apple(d["name"]):
                continue
            entry = {"id": d["id"], "path": d["path"], "size": d["size"], "label": label, "partial": d.get("partial",False)}
            owner, candidates = matcher.owner(d["name"])
            if owner:
                totals[owner]["dataBytes"] += d["size"]
                totals[owner]["locations"].append(entry)
            elif d["size"] >= MIN_UNMATCHED_BYTES and d["name"].lower() not in TOOL_FOLDERS:
                possibly = [apps[c]["name"] for c in candidates]
                unmatched.append({**entry, "name": d["name"], "possibly": possibly})

    ranked = [app for app in totals.values() if app["appBytes"] + app["dataBytes"] > 0]
    for app in ranked:
        app["total"] = app["appBytes"] + app["dataBytes"]
        app["partial"] = by_path.get(app["appPath"],{}).get("partial",False) or any(e.get("partial") for e in app["locations"])
        app["locations"].sort(key=lambda e: e["size"], reverse=True)
    ranked.sort(key=lambda a: a["total"], reverse=True)
    unmatched.sort(key=lambda e: e["size"], reverse=True)
    return {"apps": ranked, "unmatched": unmatched}
