"""Detect whether a path belongs to a code project.

Projects keep intentional copies of files (public/ and dist/ both hold the
same image), so removing one copy breaks the project. Duplicate search skips
anything inside one.
"""

import os
from pathlib import Path

PROJECT_MARKERS = frozenset({
    ".git",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Package.swift",
    "Gemfile",
    "composer.json",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "CMakeLists.txt",
})
PROJECT_SUFFIXES = (".xcodeproj", ".xcworkspace")


def _is_project_folder(folder):
    try:
        names = os.listdir(folder)
    except OSError:
        return False
    return any(name in PROJECT_MARKERS or name.endswith(PROJECT_SUFFIXES) for name in names)


def project_root(path, home, cache=None):
    """The nearest project folder above ``path`` (below ``home``), or None.

    ``path`` itself is not considered, so a whole project folder can still be
    compared with another copy of it. Pass a dict as ``cache`` to share
    directory lookups across many calls.
    """
    cache = {} if cache is None else cache
    home = Path(home)
    for folder in Path(path).parents:
        if folder == home or home not in folder.parents:
            return None
        if folder not in cache:
            cache[folder] = _is_project_folder(folder)
        if cache[folder]:
            return str(folder)
    return None
