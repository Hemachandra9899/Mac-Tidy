# Security and safety model

Mac Tidy can move your files, so its main job is to make wrong moves hard. This document describes the safeguards. Please report bypasses privately (see the end).

## Local-only server

- Binds to `127.0.0.1` only (port 8765 by default; `MAC_TIDY_PORT` overrides it).
- Every request must carry a `Host` header matching the configured local port (`127.0.0.1:8765` or `localhost:8765` by default), which blocks DNS rebinding.
- Every mutating request (POST) also needs a matching `Origin` and a per-process session token, which blocks cross-site requests.
- Only files under `src/mac_tidy/web/` with known extensions are served. Path traversal and hidden files are refused.
- Responses send `Content-Security-Policy`, `X-Frame-Options: DENY`, `nosniff` and `no-store`.

## Moving an item to Trash

1. **Selection.** The browser sends an item's index *and* its path. The server resolves the index in its own report and refuses the request if the path differs.
2. **Policy.** `policy.py` re-derives eligibility from the path alone. The browser's category is never trusted. The policy is an allowlist (see README).
3. **Preview.** The server fingerprints the item: no symlinks anywhere in its path, and its device, inode, modification time and size. It then issues a random approval key that expires in 5 minutes. Nothing moves at this step.
4. **Approval.** The user must tick a confirmation. The key is single-use and tied to the scan revision. The server re-checks the fingerprint and the policy.
5. **Native move.** The Swift helper re-checks the symlink rule and the fingerprint immediately before calling `FileManager.trashItem`. The item stays recoverable with Finder's Put Back.
6. **Record.** The move is appended to the activity log atomically (write a temp file, then rename).

Moves run one at a time, and a rescan cannot start while a move is in progress. The helper runs in its own process session, so pressing Control-C in the launcher's Terminal cannot interrupt a move before it is recorded. On shutdown the server waits for any in-flight move to finish.

## Known limits

- There is a small window between the helper's final check and `trashItem`. It is narrowed, not eliminated.
- If macOS takes longer than 120 seconds, the move is reported as unfinished and may still complete. The UI tells the user to check Trash before retrying.
- Sizes are estimates. APFS clones and snapshots can mean less space is reclaimed than shown.

## Reporting a vulnerability

Please open a private security advisory on the repository (GitHub → Security → Report a vulnerability) rather than a public issue.

## Storage insights and content access

The regular scan reads filesystem metadata. Per-app matching additionally reads installed apps’ `Info.plist` files. Duplicate searches read personal file contents only after the user starts one. They are limited to the indexed local Documents, Downloads and Desktop inventory, a chosen I/O budget, and explicit candidate/entry limits. Cloud placeholders, symlinks, packages and dependency trees are excluded. Equal size or edge samples never count as confirmed duplicates: full SHA-256 verification is required.

Duplicate-file approvals check both the selected copy and the copy to keep against their verified fingerprints. Approval checks the keeper again before moving the selected copy. This reduces accidental loss but cannot prevent another app changing the keeper immediately afterward. Folder matches are inspection-only.

Scan reports, history and activity remain in the local data directory. History keeps up to 60 capacity points and only two full folder baselines. There is no telemetry, AI analysis or external upload. Permission-denied locations remain partial; an absent owner match or old modification time never grants additional Trash permission.
