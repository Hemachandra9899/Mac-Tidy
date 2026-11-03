"""Path rules: what a location holds, and whether it may be moved to Trash."""

from .classify import classify
from .policy import action_policy

__all__ = ["action_policy", "classify"]
