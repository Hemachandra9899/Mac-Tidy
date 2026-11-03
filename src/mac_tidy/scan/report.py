"""Turn a raw scan into the compact report the dashboard browses."""

from ..rules import action_policy, classify

MIN_INDEXED_DIR_BYTES = 1_000_000
MIN_RECOMMENDED_CACHE_BYTES = 50_000_000


def _kept_ids(dirs, file_parents):
    """Folders worth browsing, plus every ancestor so the tree stays connected."""
    keep = {
        d["id"]
        for d in dirs
        if d["size"] >= MIN_INDEXED_DIR_BYTES or d["parent"] is None or d["partial"] or d["id"] in file_parents
    }
    for i in list(keep):
        parent = dirs[i]["parent"]
        while parent is not None and parent not in keep:
            keep.add(parent)
            parent = dirs[parent]["parent"]
    return keep


def _annotate(rows, item_type):
    for row in rows:
        row.update(classify(row["path"]))
        row["trashPolicy"] = action_policy(row, item_type)


def prepare_report(result):
    """Keep browsable folders, renumber ids and attach category and Trash policy.

    Kept: folders of at least 1 MB, roots, partially scanned folders, parents
    of indexed files, and their ancestors. Safe to run on a prepared report.
    """
    keep = _kept_ids(result["dirs"], {f["parent"] for f in result["files"]})
    retained = [d for d in result["dirs"] if d["id"] in keep]
    new_id = {d["id"]: i for i, d in enumerate(retained)}
    for d in retained:
        d["id"] = new_id[d["id"]]
        d["parent"] = new_id.get(d["parent"])
    for f in result["files"]:
        f["parent"] = new_id[f["parent"]]

    root_paths = {d["path"] for d in result["roots"]}
    result["dirs"] = retained
    result["roots"] = [d for d in retained if d["path"] in root_paths]
    _annotate(retained, "dir")
    _annotate(result["files"], "file")
    return result


def recommendations(report, was_moved):
    """Largest eligible caches, without listing a cache inside another one."""
    if not report:
        return []
    found = []
    for d in sorted(report["dirs"], key=lambda d: d["size"], reverse=True):
        eligible = d["kind"] == "cache" and d["size"] >= MIN_RECOMMENDED_CACHE_BYTES and d["trashPolicy"]["allowed"]
        if not eligible or was_moved(d["path"]):
            continue
        if any(d["path"].startswith(x["path"] + "/") for x in found):
            continue
        found.append({**d, "type": "dir"})
    return found
