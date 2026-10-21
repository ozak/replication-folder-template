#!/usr/bin/env python3
"""
Fill the template's {{token}} placeholders in a replication folder from the package's own
information file, <target>/replication-info.json (see project_info.py): title, authors (all
co-authors, with links, affiliations, ORCIDs), citation, compute specs and logos.

Usage:
    python apply_defaults.py <target-dir> [--info <target>/replication-info.json] [--dry-run]

The author list must have been confirmed by the user (project_info.py confirm); otherwise the
author tokens are left in place and the script exits with an error. Tokens without a value are
reported so the agent can ask for them. Binary files and .git are skipped.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable  # noqa: E402
from project_info import load, tokens  # noqa: E402

SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg", ".gif", ".zip", ".gz", ".tar", ".pkl",
                   ".dta", ".parquet", ".pyc", ".so", ".skill"}
TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target_dir", type=Path)
    ap.add_argument("--info", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    t = a.target_dir
    info_path = a.info or t / "replication-info.json"
    if not info_path.exists():
        sys.exit(f"⚠️  {info_path} not found — create it with project_info.py (extract / set) and confirm it with the user.")
    info = load(info_path)
    if not info.get("confirmed"):
        sys.exit("⚠️  The author list in replication-info.json is not confirmed by the user yet "
                 "(show it with project_info.py show, then project_info.py confirm).")
    T = {k: ("" if v is None else str(v)) for k, v in tokens(info).items()}
    important = {"title", "year", "authors_and", "laptop_specs", "laptop_memory"}

    total, unfilled = 0, set()
    for f in sorted(t.rglob("*")):
        if not f.is_file() or f.suffix.lower() in SKIP_EXTENSIONS or ".git" in f.parts or "_migration" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        found = set(TOKEN_RE.findall(text))
        if not found:
            continue
        new = TOKEN_RE.sub(lambda m: T.get(m.group(1), m.group(0)), text)
        unfilled |= {x for x in found if x not in T or (x in important and not T[x])}
        n = sum(1 for x in found if x in T)
        if n and not a.dry_run and new != text:
            assert_writable(f)
            f.write_text(new, encoding="utf-8")
        if n:
            print(f"  {f.relative_to(t)}: {n} token(s){' (dry run)' if a.dry_run else ''}")
            total += n
    print(f"✅ {total} token(s) filled from {info_path.name}")
    if unfilled:
        print(f"⚠️  still unfilled (ask the user, then project_info.py set ...): {sorted(unfilled)}")


if __name__ == "__main__":
    main()
