"""Identify an item precisely enough to prove a later move targets the same item."""

import os
import stat
from pathlib import Path


def fingerprint(path):
    """Return ``[device, inode, mtime_ns, size]`` for a regular file or directory.

    Rejects symlinks anywhere in the path. The Swift helper computes the same
    values and refuses to move the item if they differ.
    """
    p = Path(path)
    if str(p.resolve(strict=True)) != str(p.absolute()):
        raise ValueError("A symlink is present. Reveal and review this item in Finder instead.")
    s = os.lstat(path)
    if stat.S_ISLNK(s.st_mode) or not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode)):
        raise ValueError("Unsupported file type or symlink")
    return [s.st_dev, s.st_ino, s.st_mtime_ns, s.st_size]
