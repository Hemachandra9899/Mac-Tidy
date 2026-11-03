<p align="center">
  <img src="assets/app-icon.png" width="128" alt="Mac Tidy" />
</p>

# Mac Tidy

<p align="center">
  <b>See where your Mac's storage went, and clean it up one reviewed item at a time</b>
</p>
<p align="center">
  A local dashboard that measures your disk, suggests safe caches to remove, and only ever moves things to the Trash.
</p>

<div align="center">

  <img src="https://img.shields.io/badge/Status-Working%20Prototype-299B50?style=for-the-badge&labelColor=0F2A1A" alt="Status" />
  <img src="https://img.shields.io/badge/Stack-Python%20%7C%20Swift%20%7C%20JavaScript-299B50?style=for-the-badge&labelColor=0F2A1A" alt="Stack" />
  <img src="https://img.shields.io/badge/Platform-macOS-299B50?style=for-the-badge&labelColor=0F2A1A" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-299B50?style=for-the-badge&labelColor=0F2A1A" alt="License" />

</div>

<br>

## <img src="https://api.iconify.design/lucide/telescope.svg?color=%23299B50" width="20" height="20">&nbsp; The Problem
Freeing space on a Mac is oddly risky. The usual tools each get one part wrong.

<table width="100%">
  <tr>
    <td width="33%" valign="top" align="center">
      <br>
      <h3 align="center"><img src="https://api.iconify.design/lucide/circle-help.svg?color=%23299B50" width="18" height="18">&nbsp; Where did it go?</h3>
      <p align="center">"System Data" is a black box. You can't tell whether 180 GB is a build cache or something you need.</p>
      <br>
    </td>
    <td width="33%" valign="top" align="center">
      <br>
      <h3 align="center"><img src="https://api.iconify.design/lucide/bomb.svg?color=%23299B50" width="18" height="18">&nbsp; One-click cleaners</h3>
      <p align="center">"Clean everything" buttons delete in bulk and permanently. A wrong guess costs you real data.</p>
      <br>
    </td>
    <td width="33%" valign="top" align="center">
      <br>
      <h3 align="center"><img src="https://api.iconify.design/lucide/cloud-upload.svg?color=%23299B50" width="18" height="18">&nbsp; Your data leaves</h3>
      <p align="center">Many cleaners are closed-source, want broad permissions, and phone home with a list of your files.</p>
      <br>
    </td>
  </tr>
</table>

<br>

## <img src="https://api.iconify.design/lucide/cpu.svg?color=%23299B50" width="20" height="20">&nbsp; The Solution
Mac Tidy treats cleanup as a **review problem**, not a deletion problem. It measures first, explains every location in plain words, and puts you in the loop for each move. Nothing is deleted: approved items go to the Trash, where Finder's **Put Back** restores them.

- **Local only.** A small server on `127.0.0.1` serves the dashboard. No accounts, no telemetry, no third-party packages.
- **Review first.** Every move needs a preview, a checkbox and a single-use approval that expires after five minutes.
- **Allowlist, not blocklist.** Only recognised caches, logs and your own Downloads/Documents/Desktop files can be offered. Everything else is refused.

### How it works
<p align="center">
  <img src="assets/architecture.svg" width="auto" height="400" alt="Architecture diagram" />
</p>

1.  **Scan:** The scanner walks your home folder, `/Applications`, `/Library` and a few system paths. It reads metadata only, never file contents, never follows symlinks, stays on one volume and counts hard links once. Sizes are allocated bytes (`st_blocks × 512`).
2.  **Classify:** Each folder and file is labelled by a rule table: cache, logs, downloads, developer data, backup, system, or "keep unless unneeded", with advice for each.
3.  **Suggest:** Caches of 50 MB or more become suggestions. A cache nested inside another suggestion is counted once.
4.  **Preview:** You pick an item. The server checks the allowlist again from the path alone, fingerprints the item (device, inode, modification time, size, no symlinks) and issues a random approval key. Nothing has moved yet.
5.  **Approve:** You tick a confirmation that you've stopped the app or no longer need the file. The key is single-use and tied to this scan. The server re-checks the fingerprint.
6.  **Move:** The Swift helper checks the fingerprint once more, then calls Apple's `FileManager.trashItem`. The move is written to an activity log so you can find it later.
7.  **Recover or reclaim:** Use **Activity & Recovery** to show the item in Trash and Put Back, or empty Trash yourself and rescan to measure the space you freed. Mac Tidy never empties Trash.

<br>

## <img src="https://api.iconify.design/lucide/shield-check.svg?color=%23299B50" width="20" height="20">&nbsp; Security Model

| **Concern**                | **What Mac Tidy does**                                                                                      |
| :------------------------- | :---------------------------------------------------------------------------------------------------------- |
| **Network exposure**       | Binds to `127.0.0.1` only. Requests must carry an allowed `Host`, which blocks DNS rebinding.               |
| **Other websites**         | Every mutating request needs a matching `Origin` and a per-process session token, which blocks cross-site requests. |
| **Wrong item**             | The browser sends an item's index and path. The server uses its own report and refuses if they disagree.   |
| **Item changed after review** | The fingerprint is checked at approval and again inside the helper. A changed item needs a fresh review. |
| **Symlinks**               | Refused anywhere in an item's path.                                                                         |
| **Crash or Control-C mid-move** | The helper runs in its own session, and shutdown waits for an in-flight move to be recorded.          |
| **Permanent loss**         | Nothing is deleted. Items go to the Trash and stay recoverable.                                             |
| **Your data**              | Nothing leaves your Mac. Scan results and the activity log live in `~/Library/Application Support/Mac Tidy/`. |

### What can be moved to Trash
Only items inside your home folder that match the allowlist:

- individual app caches under `~/Library/Caches/…`, plus npm, pip, uv and Webpack build caches
- individual folders under `~/Library/Logs/…`
- individual files in Downloads, Documents and Desktop

These are always refused: system locations, Apple-managed data, whole `Library` or `Caches` folders, credentials (`.ssh`, `.aws`, `.gnupg`), source control (`.git`), the Trash itself, hidden personal files, anything reached through a symlink, and anything *inside* an app or library package (`.app`, `.photoslibrary`, `.fcpbundle` and similar). See [SECURITY.md](SECURITY.md) for the full model and its known limits.

<br>

## <img src="https://api.iconify.design/lucide/layout-dashboard.svg?color=%23299B50" width="20" height="20">&nbsp; The Dashboard

| **View**                  | **What it shows**                                                                   |
| :------------------------ | :---------------------------------------------------------------------------------- |
| **Overview**              | Free space, the largest cleanup opportunity, app caches and large app data          |
| **Review Cleanup**        | Independent cache suggestions with exact paths, sizes and reasons                   |
| **Browse Storage**        | A drill-down treemap of scanned folders                                             |
| **Large Files**           | The 1,500 largest files, searchable and filterable                                  |
| **All Candidates**        | Caches, logs, downloads, developer data and backups to review                       |
| **Activity & Recovery**   | Completed moves, and whether each item is still in Trash                            |
| **Scan Details**          | Coverage, unreadable locations and why totals can't match macOS exactly             |

Moving an item to Trash does not free space until you empty Trash. Rescan afterwards to measure the result.

<br>

## <img src="https://api.iconify.design/lucide/layers.svg?color=%23299B50" width="20" height="20">&nbsp; Tech Stack
No runtime dependencies. The Python standard library, plain ES modules and CSS, and one small Swift file.

| **Component**        | **Technology**                                                                           | **Description**                                                                   |
| :------------------- | :--------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------- |
| **Server**           | <img src="https://skillicons.dev/icons?i=python" valign="middle" />                      | Python 3.10+, `http.server`. Scan, rules, approvals, activity log and the JSON API. |
| **Dashboard**        | <img src="https://skillicons.dev/icons?i=js,css,html" valign="middle" />                 | Vanilla ES modules. `core/` state, `components/`, one module per `views/` screen.  |
| **Native helper**    | <img src="https://skillicons.dev/icons?i=swift,apple" valign="middle" />                 | One Swift file: reveal in Finder, and move to Trash after re-verifying the item.   |
| **Icons**            | <img src="https://api.iconify.design/lucide/shapes.svg?color=%23299B50" width="36" valign="middle" /> | Apple SF Symbols, exported to PNG and drawn as CSS masks so they follow the theme. |

<br>

## <img src="https://api.iconify.design/lucide/rocket.svg?color=%23299B50" width="20" height="20">&nbsp; Getting Started

### Requirements
- macOS
- Python 3.10+
- Xcode Command Line Tools (`xcode-select --install`), used to compile the Swift helper

### Run it

```bash
git clone <this repo> mac-tidy && cd mac-tidy
make run
```

`make run` builds the helper on first use, starts the server and opens <http://127.0.0.1:8765>. Press Control-C to stop. You can also double-click **Start Mac Tidy.command**.

### Install as a command

```bash
make helper && pip install .
mac-tidy              # or: mac-tidy --no-open
```

### A note on measurement
Allocated sizes are estimates. APFS clones, compression, snapshots and privacy-protected folders mean totals can't be reconciled exactly with macOS Storage settings, and what you reclaim may be less than what's shown. Granting your terminal Full Disk Access (optional) lets the scan read more locations.

<br>

## <img src="https://api.iconify.design/lucide/folder-tree.svg?color=%23299B50" width="20" height="20">&nbsp; Project Layout

```
src/mac_tidy/
  cli.py            command-line entry point (`mac-tidy`, `python -m mac_tidy`)
  config.py         paths, host and port
  rules/            what a path holds (classify) and whether it may be trashed (policy)
  scan/             metadata-only filesystem scan and the browsable report
  cleanup/          moving items to Trash
    fingerprint.py    prove a later move targets the same item
    approvals.py      single-use, expiring approvals
    activity.py       persistent log of completed moves
    native.py         bridge to the Swift helper
  server/           app.py (state and use cases), http.py (routing, headers), static.py
  common/           atomic JSON file writes
  web/
    js/
      core/           api, state, selectors, format (no DOM)
      components/     reusable UI pieces: dialog, toast, metrics, item table, folder row…
      views/          one module per dashboard screen
      app/            render, actions, events, server sync
    styles/           base, layout, components, views, dark theme, responsive
    icons/            SF Symbols exported as PNG masks
native/
  MacTidyHelper.swift   reveal in Finder, move to Trash (re-verifies identity)
```

Dependencies point one way: `rules` ← `scan`, `cleanup` ← `server` ← `cli`; and on the frontend `core` ← `components` ← `views` ← `app`. See [CONTRIBUTING.md](CONTRIBUTING.md) to get involved.

<br>

## <img src="https://api.iconify.design/lucide/map.svg?color=%23299B50" width="20" height="20">&nbsp; Roadmap
- [x] **Scan:** metadata-only, no symlinks, hard links counted once, partial coverage flagged
- [x] **Explain:** every location classified with plain-language advice
- [x] **Review-first Trash:** preview, confirmation, single-use expiring approval
- [x] **Identity check:** fingerprint verified by the server and again by the native helper
- [x] **Recovery:** activity log with live "still in Trash" status and Show in Trash
- [x] **Package protection:** nothing inside an app or library bundle can be moved
- [x] **Light and dark appearance**, responsive layout
- [ ] **Screenshots** in this README
- [ ] **Signed and notarised release** so it can be double-clicked without building
- [ ] **Duplicate file finder**
- [ ] **Scheduled rescans** with a quiet notification when a cache grows large

These last items are ideas, not commitments.

<br>

## <img src="https://api.iconify.design/lucide/heart-handshake.svg?color=%23299B50" width="20" height="20">&nbsp; Acknowledgements
- [Apple SF Symbols](https://developer.apple.com/sf-symbols/): the interface icons
- [Apple's storage guidance](https://support.apple.com/en-us/102624): the reference for how macOS accounts for space

Mac Tidy is released under the [MIT License](LICENSE).

<br>

<div align="center">

[![Email](https://img.shields.io/badge/Email-34A853?style=flat&logo=gmail&logoColor=white)](mailto:pottingari@gmail.com)

</div>

<p align="center">
  <sub>Made with &nbsp;<sub><img src="https://api.iconify.design/lucide/heart.svg?color=%23299B50" width="14" height="14"></sub>&nbsp; for tidy Macs</sub>
</p>
