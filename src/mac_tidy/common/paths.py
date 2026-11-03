"""Conservative local personal-file scope for age and duplicate review."""

import stat
from pathlib import Path

from ..rules.policy import PACKAGE_SUFFIXES

PERSONAL_FOLDERS = ("Documents", "Downloads", "Desktop")
EXCLUDED_NAMES = {"node_modules", "venv", ".venv", "__pycache__", "site-packages", "Library"}
PARTIAL_DOWNLOAD_SUFFIXES = (".icloud", ".download", ".crdownload", ".part")
# Darwin SF_DATALESS: the content is not stored locally (an iCloud placeholder).
DATALESS_FLAG = 0x40000000


def personal_path(path, home):
    """True for a file or folder under Documents, Downloads or Desktop that is
    not hidden, a dependency tree, an app/library package or a partial download."""
    try:
        parts = Path(path).relative_to(Path(home)).parts
    except ValueError:
        return False
    if len(parts) < 2 or parts[0] not in PERSONAL_FOLDERS:
        return False
    excluded = any(
        part.startswith(".") or part in EXCLUDED_NAMES or part.lower().endswith(PACKAGE_SUFFIXES)
        for part in parts
    )
    return not excluded and not str(path).lower().endswith(PARTIAL_DOWNLOAD_SUFFIXES)


def local_regular(st):
    """True for a regular file whose content is stored on this Mac."""
    if not stat.S_ISREG(st.st_mode) or getattr(st, "st_flags", 0) & DATALESS_FLAG:
        return False
    return st.st_size == 0 or st.st_blocks > 0
