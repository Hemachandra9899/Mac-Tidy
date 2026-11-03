#!/bin/zsh
# Double-click to build the native helper if needed, start Mac Tidy and open the dashboard.
cd -- "${0:A:h}"
[[ -x src/mac_tidy/bin/mac-tidy-helper ]] || make helper || exit 1
PYTHONPATH=src exec python3 -m mac_tidy
