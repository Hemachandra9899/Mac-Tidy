"""Single-use, identity-bound approvals for moving items to Trash."""

import secrets
import threading
import time

from ..config import HOME
from ..rules import action_policy
from .fingerprint import fingerprint

APPROVAL_TTL_SECONDS = 300
PRIVATE_PLAN_FIELDS = ("fingerprint", "revision", "keep")


class TrashManager:
    """Issues approvals for reviewed items and carries out approved moves.

    ``mover(path, fingerprint)`` performs the move and returns the item's path
    in Trash. It must re-verify the fingerprint itself.
    """

    def __init__(self, activity, mover, home=HOME):
        self.activity = activity
        self.mover = mover
        self.home = home
        self.pending = {}
        self._lock = threading.Lock()  # guards pending
        self._move_lock = threading.Lock()  # one move at a time

    def _check_policy(self, row, item_type):
        policy = action_policy(row, item_type, self.home)
        if not policy["allowed"]:
            raise ValueError(policy["reason"])
        return policy

    def _take(self, key):
        """Remove and return a pending plan; an approval can be used only once."""
        with self._lock:
            plan = self.pending.pop(key, None)
        if not plan or plan["expires"] < time.time():
            raise ValueError("Approval expired or already used. Review the item again.")
        return plan

    def _check_keeper(self, key):
        """For an approval that depends on another copy staying put (a duplicate),
        confirm that copy is unchanged. Does not use up the approval."""
        with self._lock:
            plan = self.pending.get(key)
        keep = plan and plan.get("keep")
        if not keep:
            return
        try:
            current = fingerprint(keep["path"])
        except OSError:
            raise ValueError("The copy to keep is missing. Nothing was moved.") from None
        if current != keep["fingerprint"]:
            raise ValueError("The copy to keep changed. Run duplicate search again.")

    def preview(self, row, item_type, revision, keep=None):
        """Validate an item and issue an approval key. Moves nothing.

        ``keep`` is ``{'path', 'fingerprint'}`` of a copy that must still be
        unchanged when the move is approved. It expires with the approval.
        """
        policy = self._check_policy(row, item_type)
        key = secrets.token_urlsafe(32)
        plan = {
            "approval": key,
            "path": row["path"],
            "size": row["size"],
            "kind": row["kind"],
            "advice": row.get("advice", policy["reason"]),
            "type": item_type,
            "expires": time.time() + APPROVAL_TTL_SECONDS,
            "fingerprint": fingerprint(row["path"]),
            "revision": revision,
            "keep": keep,
        }
        with self._lock:
            now = time.time()
            self.pending = {k: v for k, v in self.pending.items() if v["expires"] > now}
            self.pending[key] = plan
        return {k: v for k, v in plan.items() if k not in PRIVATE_PLAN_FIELDS}

    def execute(self, key, revision):
        """Move an approved item to Trash after re-checking everything."""
        with self._move_lock:
            self._check_keeper(key)
            plan = self._take(key)
            if revision != plan["revision"]:
                raise ValueError("The scan changed. Review the item again.")
            try:
                current = fingerprint(plan["path"])
            except OSError:
                raise ValueError("The item changed or no longer exists. Rescan.") from None
            if current != plan["fingerprint"]:
                raise ValueError("The item changed after review. Review it again.")
            self._check_policy(plan, plan["type"])

            trash_path = self.mover(plan["path"], plan["fingerprint"])
            return self.activity.record(plan["path"], trash_path, plan["size"])
