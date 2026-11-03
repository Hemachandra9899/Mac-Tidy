# Mac Tidy: storage problems and implementation decisions

Research reviewed 3 November 2026. This is qualitative desk research, not a representative survey. Reddit posts are anecdotes and vendor posts were not treated as independent validation. Searches of indexed X/Twitter posts did not yield a sufficiently useful attributable result; no X sentiment is claimed.

## Problems observed

1. **“What is System Data, and can I delete it?”** A user facing hundreds of GB asks what the category means and whether removing it risks data loss ([Reddit discussion, August 2026](https://www.reddit.com/r/mac/comments/1w2wp8x/system_data_381_gb_what_is_it_can_i_delete_it_is/)). Product inference: show paths, owners, evidence and reviewable actions rather than one unexplained “junk” number.
2. **“I deleted things but free space went down.”** Reports describe contradictory free-space/app totals and delayed reclamation ([Reddit, November 2024](https://www.reddit.com/r/MacOS/comments/1gh810z/less_available_storage_after_deleting_stuff/), [another storage-total discussion](https://www.reddit.com/r/mac/comments/1gh1mya/storage_is_showing_as_full_when_its_not/), [large-folder deletion discussion](https://www.reddit.com/r/MacOS/comments/pabdbk/space_not_free_after_deleting_large_folder/)). Product inference: distinguish bytes moved to Trash from actual available-space changes; explain APFS and snapshots without promising exact savings.
3. **Developer storage needs tool-specific explanations.** Docker documents that its disk image has a maximum size distinct from actual allocation ([Docker Mac FAQ](https://docs.docker.com/desktop/troubleshoot-and-support/faqs/macfaqs/)). Docker’s [pruning documentation](https://docs.docker.com/engine/manage-resources/pruning) reinforces that reclaiming its data is an explicit operation with resource-specific effects. Product inference: explain tool storage and show inspection commands, never treat a database/disk image as a disposable cache.
4. **Duplicate review needs trustworthy evidence.** Size alone and visually similar images do not establish identical content. This is an engineering decision rather than a quantified market finding: verify full file hashes, show every path and require a keeper.

## Primary technical references

- [Apple: local Time Machine snapshots](https://support.apple.com/en-us/102154): macOS manages snapshots and includes their space in availability accounting. Mac Tidy lists names without inventing snapshot byte sizes.
- [Apple: available capacity for important use](https://developer.apple.com/documentation/foundation/urlresourcevalues/volumeavailablecapacityforimportantusage): a native capacity estimate, not an exact list of deletable files.
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines): retained the app’s macOS-style sidebar, system typography, grouped rows, explicit dialogs and green accent. This browser UI is not a native AppKit control implementation.

## Implemented

- Per-app measured bundle/data totals, matched by app identifiers and names; ambiguous Library folders remain separate.
- Developer explanations for supported tools and project dependencies; age uses the latest observed modification in the project. No project is asserted to be unused.
- Older personal files with 90/180/365/730-day filters; modification age is stated explicitly.
- Up to 60 real scan capacity points, with comparable complete-folder growth/shrinkage and only two full folder baselines retained.
- Opt-in, cancellable exact file/folder searches with a declared read budget. Files use size, edge samples and full SHA-256; folders verify relative names, empty directories and full content hashes. Folder results are inspection-only.
- Duplicate-file keeper selection and per-copy native Trash approval, retaining existing policy, fingerprints and activity records.
- Free-space explanations and native capacity estimates; unavailable measurements are shown as unavailable, not zero.
- Run instructions now use the real GitHub remote, identify make as part of Xcode Command Line Tools, and document an alternate port.

## Limits and next priorities

Regular scans remain metadata-only. Personal review indexes the largest 10,000 eligible local files of at least 1 MB; general largest-file inventory is capped at 1,500. Duplicate folders use at most 100 size candidate groups and 10,000 entries per folder. Read budgets apply to each search; exclusions and incomplete coverage are disclosed. APFS clones can share blocks, so repeated logical bytes are not guaranteed reclaimed disk bytes.

Not included: automatic cleanup, broad folder deletion, similar-photo matching, cloud-file hydration, snapshot deletion, a signed/notarized app, scheduled jobs, incremental rescans or dashboard Put Back. Recovery remains Finder’s native Put Back. Future work should prioritize clearer running-app warnings and scan performance before unattended cleanup.
