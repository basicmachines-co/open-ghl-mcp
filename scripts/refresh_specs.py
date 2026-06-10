#!/usr/bin/env python3
"""Refresh the vendored GoHighLevel OpenAPI specs and report catalog drift.

Re-fetches the official app specs, compares the resulting catalog against the
committed one, and reports added/removed endpoints plus endpoints whose token
level is only a default guess (scope tag not yet confirmed).

Usage:
    python scripts/refresh_specs.py            # report only (no writes)
    python scripts/refresh_specs.py --apply    # overwrite specs/ghl/ with latest
    python scripts/refresh_specs.py --check     # exit 1 if drift detected (CI)
"""

import argparse
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

# Allow running as a script (no package install needed).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gateway.catalog import load_catalog, SPECS_DIR, SUPPLEMENTAL_PATH  # noqa: E402
from src.gateway.drift import diff_catalogs, unclassified_endpoints  # noqa: E402

RAW_BASE = "https://raw.githubusercontent.com/GoHighLevel/highlevel-api-docs/main/"
TREE_API = (
    "https://api.github.com/repos/GoHighLevel/highlevel-api-docs/"
    "git/trees/main?recursive=1"
)


def fetch_app_specs(dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(TREE_API, timeout=60) as r:
        tree = json.loads(r.read())
    apps = [
        t["path"]
        for t in tree.get("tree", [])
        if t["path"].startswith("apps/") and t["path"].endswith(".json")
    ]
    for p in apps:
        with urllib.request.urlopen(RAW_BASE + p, timeout=60) as r:
            data = r.read()
        json.loads(data)  # validate
        (dest / Path(p).name).write_bytes(data)
    return len(apps)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="overwrite specs/ghl/")
    ap.add_argument("--check", action="store_true", help="exit 1 on drift (CI)")
    args = ap.parse_args()

    committed = load_catalog()  # spec ∪ supplemental, current

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp) / "ghl"
        n = fetch_app_specs(tmpdir)
        latest = load_catalog(specs_dir=tmpdir, supplemental_path=SUPPLEMENTAL_PATH)
        print(f"Fetched {n} app specs; {len(latest)} endpoints in latest catalog.")

        diff = diff_catalogs(committed, latest)
        print(f"\nAdded ({len(diff['added'])}):")
        for k in diff["added"]:
            print(f"  + {k}")
        print(f"\nRemoved ({len(diff['removed'])}):")
        for k in diff["removed"]:
            print(f"  - {k}")

        unclassified = unclassified_endpoints(latest)
        print(f"\nUnclassified token level ({len(unclassified)}) — confirm scope tags:")
        for e in sorted(unclassified, key=lambda e: e.path)[:50]:
            print(f"  ? {e.method} {e.path} [{e.scope or 'no-scope'}]")

        drift = bool(diff["added"] or diff["removed"])

        if args.apply:
            n2 = fetch_app_specs(SPECS_DIR)
            print(f"\nApplied: wrote {n2} specs to {SPECS_DIR}")

    if args.check and drift:
        print("\nDrift detected (see above).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
