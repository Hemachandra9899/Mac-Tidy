# Contributing

Thanks for helping. Mac Tidy deliberately has no runtime dependencies: the Python standard library, plain ES modules and CSS, and one small Swift file. Please keep it that way.

## Setup

```sh
make helper      # compile native/MacTidyHelper.swift
make run         # start the server and open the dashboard
```

## Guidelines

- **Safety first.** Any change to `policy.py`, `trash.py` or the Swift helper should make Trash moves stricter or keep them equally strict. Explain the reasoning in the pull request.
- **Never move real user data in tests.** Use fixtures you create, inside a temporary folder.
- **Python:** PEP 8, standard library only.
- **Frontend:** one module per view in `web/js/views/`, shared UI pieces in `web/js/components/`. Escape every interpolated value with `esc()`. Styles go in the matching file under `web/styles/`.
- **Icons:** SF Symbols exported with `mac-tidy-helper icon <out.png> <symbol-name>`.

## Before opening a pull request

Run your local test suite and check the dashboard in both light and dark appearance.
