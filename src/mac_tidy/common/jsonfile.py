"""JSON persistence that never leaves a half-written file behind."""

import json
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json_atomic(path, data):
    """Write to a sibling temp file, then rename it over ``path``."""
    path = Path(path)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data))
    temp.replace(path)
