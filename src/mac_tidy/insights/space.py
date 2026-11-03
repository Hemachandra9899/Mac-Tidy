"""Why free space looks wrong: purgeable space, local snapshots and the Trash."""

import os
import subprocess
from pathlib import Path

from ..scan import data_volume, scan_tree

SNAPSHOT_PREFIX = "com.apple."


def local_snapshots(volume="/"):
    """Names of Time Machine local snapshots, or None if they can't be listed."""
    try:
        output = subprocess.run(
            ["/usr/bin/tmutil", "listlocalsnapshots", volume],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return [line.strip() for line in output.splitlines() if line.strip().startswith(SNAPSHOT_PREFIX)]


def trash_size(home):
    """Allocated bytes in the user's Trash, or None when macOS privacy blocks reading it."""
    trash = Path(home) / ".Trash"
    try:
        os.listdir(trash)
    except OSError:
        return None
    return sum(root["size"] for root in scan_tree([str(trash)])["roots"])


def space_summary(volume_space, home):
    """Free space now versus what macOS could free, and where the gap comes from.

    ``volume_space(path)`` returns ``{'total', 'free', 'freeIncludingPurgeable'}``.
    """
    try:
        capacity = volume_space(data_volume())
    except ValueError:
        capacity = None
    snapshots = local_snapshots()
    return {
        "capacity": capacity,
        "purgeable": max(0, capacity["freeIncludingPurgeable"] - capacity["free"]) if capacity else None,
        "snapshots": snapshots,
        "trashBytes": trash_size(home),
    }
