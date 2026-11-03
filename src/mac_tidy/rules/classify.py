"""Path classification: what kind of data a location holds and how to treat it.

Rules are checked in order; the first match wins. Matching is case-insensitive
like APFS.
"""

from dataclasses import asdict, dataclass

from ..config import HOME


@dataclass(frozen=True)
class Category:
    kind: str
    label: str
    advice: str


SYSTEM = Category(
    "system",
    "Managed files",
    "Use the owning app, package manager or macOS Storage settings. Do not delete system folders manually.",
)
BUILD_CACHE = Category(
    "cache",
    "Rebuildable build cache",
    "Webpack build cache. Stop dev servers and build or render jobs for this project first. It is rebuilt "
    "on the next build, which will take longer. Keep the project source and the rest of node_modules.",
)
CACHE = Category(
    "cache",
    "Rebuildable cache",
    "Quit the owning app and finish active work first. Review the contents in Finder. Prefer the app’s "
    "cache-cleaning command. Caches regenerate; some offline content may need downloading again.",
)
LOGS = Category(
    "logs",
    "Logs · review",
    "Old logs may be removable after quitting the app. Keep recent logs if investigating a problem; do not "
    "remove the parent Library folder.",
)
DOWNLOADS = Category(
    "downloads",
    "Personal file · review",
    "Check that you no longer need this download and have another copy if needed. Move only reviewed "
    "items to Trash.",
)
DEVELOPER = Category(
    "developer",
    "Developer data",
    "Use Xcode Settings to remove unused runtimes or devices. Archives can contain irreplaceable builds; "
    "do not bulk-delete this folder.",
)
BACKUP = Category(
    "backup",
    "Device backup",
    "Review device backups in Finder > your device > Manage Backups. Keep any backup you may need to restore.",
)
REVIEW = Category(
    "review",
    "Keep unless unneeded",
    "This may contain documents, models, app databases or settings. Size alone does not make it junk. "
    "Review in the owning app before deleting.",
)

SYSTEM_PREFIXES = ("/private/var", "/library", "/system", "/usr", "/opt")
CACHE_SEGMENTS = (".npm/_cacache", ".cache/pip", ".cache/uv", "library/developer/xcode/deriveddata")


def _within(p, folder):
    """True for ``folder`` itself or anything inside it (``folder`` starts with '/')."""
    return folder + "/" in p or p.endswith(folder)


def _is_cache(p, _home):
    return _within(p, "/library/caches") or any(f"/{segment}/" in p + "/" for segment in CACHE_SEGMENTS)


RULES = (
    (lambda p, _: p.startswith(SYSTEM_PREFIXES), SYSTEM),
    (lambda p, _: "/node_modules/.cache/webpack" in p, BUILD_CACHE),
    (_is_cache, CACHE),
    (lambda p, _: _within(p, "/library/logs"), LOGS),
    (lambda p, home: p.startswith(home + "/downloads/"), DOWNLOADS),
    (lambda p, _: "/library/developer/" in p, DEVELOPER),
    (lambda p, _: "/mobilesync/backup" in p, BACKUP),
)


def classify(path, home=HOME):
    """Return ``{'kind', 'label', 'advice'}`` for a path."""
    p, h = path.lower(), home.lower()
    category = next((category for matches, category in RULES if matches(p, h)), REVIEW)
    return asdict(category)
