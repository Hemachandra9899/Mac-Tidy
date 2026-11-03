"""Older personal files: modification age is evidence, never proof of disuse."""

from ..common.paths import personal_path

MIN_BYTES = 1_000_000
MIN_DAYS = 90
SECONDS_PER_DAY = 86400
SCOPE = "Local indexed personal files of at least 1 MB. Modification age does not prove a file is unused."


def review_inventory(report):
    """``(rows, type)`` for the personal-file index, falling back to the largest files."""
    if "reviewFiles" in report:
        return report["reviewFiles"], "review-file"
    return report.get("files", []), "file"


def older_files(report, now):
    rows, item_type = review_inventory(report)
    found = []
    for index, row in enumerate(rows):
        if row.get("size", 0) < MIN_BYTES or not personal_path(row["path"], report["home"]):
            continue
        age_days = max(0, int((now - row["mtime"]) // SECONDS_PER_DAY))
        if age_days >= MIN_DAYS:
            found.append({**row, "index": index, "type": item_type, "ageDays": age_days})
    found.sort(key=lambda row: row["size"], reverse=True)
    return {
        "files": found,
        "ageBasis": "modified",
        "minDays": MIN_DAYS,
        "indexedFiles": len(rows),
        "scope": SCOPE,
    }
