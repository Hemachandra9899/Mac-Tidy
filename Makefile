PYTHON ?= python3
HELPER := src/mac_tidy/bin/mac-tidy-helper
SWIFT_CACHE := $(or $(TMPDIR),/tmp)/mac-tidy-swift-cache

.PHONY: run helper test clean

run: $(HELPER)
	PYTHONPATH=src $(PYTHON) -m mac_tidy

helper: $(HELPER)

$(HELPER): native/MacTidyHelper.swift
	mkdir -p $(dir $@)
	swiftc -O -module-cache-path $(SWIFT_CACHE) $< -o $@

# Tests live in tests/, which is local-only (see .gitignore).
test: $(HELPER)
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests/unit
	node --test tests/js/*.test.mjs
	PYTHONPATH=src $(PYTHON) tests/integration/verify_native.py

clean:
	rm -rf src/mac_tidy/bin build dist src/*.egg-info
	find . -name __pycache__ -prune -exec rm -rf {} +
