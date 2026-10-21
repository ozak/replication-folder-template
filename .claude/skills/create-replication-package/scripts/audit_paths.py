#!/usr/bin/env python3
"""
Find (and optionally fix) non-portable paths in migrated code.

Usage:
    python audit_paths.py <replication-package>/progs                # report
    python audit_paths.py <replication-package>/progs --map map.json --apply   # rewrite

Flags, per file and line (code cells only for notebooks):
  ABS     absolute paths (/Users, /home, /Volumes, C:\\, ~/), cloud folders (Dropbox, Google Drive)
  CHDIR   cd / os.chdir / setwd — notebooks must run from their own folder
  UP      relative paths that do not go through ../../ (e.g. '../data/' from the old layout)
  GLOBAL  Stata globals holding paths ($path, $data ...) — define them once, relative

--map is a JSON list of [regex, replacement] pairs applied in order to code lines, e.g.
  [["/Users/ozak/Dropbox/Research/Project/data/", "../../data/"],
   ["/Volumes/My Book/GIS/GPW/", "../../raw-data/GPW/"],
   ["\\.\\./data/", "../../data/"]]
--apply edits files IN PLACE — only run it on the new package, never on the source project.
"""
import argparse
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry, probe  # noqa: E402

EXT = {".py", ".ipy", ".ipynb", ".do", ".ado", ".r", ".rmd", ".m", ".jl", ".sh", ".sbatch"}
RULES = [
    ("ABS", re.compile(r"""(/Users/|/home/|/Volumes/|/mnt/|[A-Za-z]:[\\/]|~/|Dropbox|Google ?Drive|OneDrive|iCloud)""")),
    ("CHDIR", re.compile(r"""(^\s*cd\s|os\.chdir|setwd\(|%cd\s)""")),
    ("UP", re.compile(r"""['"](?:\.\./)(?!\.\./)[\w-]""")),
    ("GLOBAL", re.compile(r"""^\s*global\s+\w*(path|dir|data|root|folder)\w*\s""", re.I)),
]


def lines_of(p: Path):
    if p.suffix.lower() == ".ipynb":
        nb = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        for ci, c in enumerate(nb.get("cells", [])):
            if c.get("cell_type") != "code":
                continue
            src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])
            for li, ln in enumerate(src.splitlines(), 1):
                yield f"cell {ci} line {li}", ln
    else:
        for li, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            yield f"line {li}", ln


def apply_map(p: Path, pairs):
    def fix(s):
        for rx, rep in pairs:
            s = re.sub(rx, rep, s)
        return s
    if p.suffix.lower() == ".ipynb":
        nb = json.loads(p.read_text(encoding="utf-8"))
        changed = False
        for c in nb.get("cells", []):
            if c.get("cell_type") != "code":
                continue
            src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])
            new = fix(src)
            if new != src:
                c["source"], changed = new, True
        if changed:
            p.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        return changed
    s = p.read_text(encoding="utf-8", errors="replace")
    new = fix(s)
    if new != s:
        p.write_text(new, encoding="utf-8")
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--map", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    files = [p for p in sorted(a.root.rglob("*")) if p.suffix.lower() in EXT and ".ipynb_checkpoints" not in p.parts]
    if a.apply:
        if not a.map:
            raise SystemExit("--apply needs --map")
        assert_writable(a.root)
        pairs = json.loads(a.map.read_text())
        n = sum(apply_map(p, pairs) for p in files)
        print(f"✅ rewrote paths in {n} file(s)")
    total = 0
    for p in files:
        hits = []
        for where, ln in lines_of(p):
            s = ln.strip()
            if s.startswith(("#", "//", "*")) and not s.startswith("#!"):
                continue
            tags = [t for t, rx in RULES if rx.search(ln)]
            if tags:
                hits.append(f"  [{','.join(tags)}] {where}: {s[:140]}")
        if hits:
            total += len(hits)
            print(f"{p}:")
            print("\n".join(hits[:40]) + (f"\n  … {len(hits) - 40} more" if len(hits) > 40 else ""))
    print(f"\n{total} suspicious line(s) in {len(files)} file(s)." + ("" if total else " ✅ All paths portable."))


if __name__ == "__main__":
    main()
