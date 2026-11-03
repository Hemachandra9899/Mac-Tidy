"""Bridge to the Swift helper that talks to Finder and the macOS Trash."""

import json
import subprocess

from ..config import HELPER_PATH

TIMEOUTS = {"trash": 120, "reveal": 20, "space": 10}


def _run(operation, *args):
    try:
        completed = subprocess.run(
            [str(HELPER_PATH), operation, *map(str, args)],
            capture_output=True,
            text=True,
            timeout=TIMEOUTS[operation],
            # Own session: Control-C in the launcher's Terminal must not kill a
            # move halfway between Trash and the activity log.
            start_new_session=True,
        )
        data = json.loads(completed.stdout)
    except subprocess.TimeoutExpired:
        raise ValueError(
            "macOS did not finish in time. Check Finder and Trash before trying again."
        ) from None
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("The native Mac helper is unavailable. Build it with `make helper`.") from error
    if not data.get("ok"):
        raise ValueError(data.get("error", "macOS could not complete this action"))
    return data


def move_to_trash(path, fingerprint):
    """Move ``path`` to Trash if it still matches ``fingerprint``. Returns its Trash path."""
    return _run("trash", path, *fingerprint)["trashPath"]


def reveal(path):
    """Select ``path`` in a Finder window."""
    _run("reveal", path)


def volume_space(path):
    """``{'total', 'free', 'freeIncludingPurgeable'}`` in bytes for the volume holding ``path``."""
    data = _run("space", path)
    return {key: data[key] for key in ("total", "free", "freeIncludingPurgeable")}
