#!/usr/bin/env python3
"""
Find the generated file behind each table whose body was pasted into the paper's .tex
("inline" entries in rename_map.json), and the code output behind complete table files the paper
\\input's ("table_file": "full" — often hand-edited copies of an esttab/stargazer output). Compares the decimal numbers in the pasted table
(the `fingerprint` stored by parse_latex.py) with every candidate output file
(.tex/.txt/.csv/.rtf/.html/.smcl/.log) in the project and reports the best matches.

Usage:
    python match_inline_tables.py --project-root <source> --rename-map rename_map.json \
        [--search tables --search output] [--update] [--min-score 0.5]

--update writes the best match (score >= --min-score) into each inline entry as
`matched_source` + `match_score` (status stays "inline": the paper must still be edited to
\\input the generated table, and the Renaming notebook must wrap the body with the caption,
column headers and notes taken from the .tex).
"""
import argparse
import json
import os
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry, probe  # noqa: E402

EXTS = {".tex", ".txt", ".csv", ".rtf", ".html", ".htm", ".smcl", ".log", ".md"}
SKIP = {".git", ".ipynb_checkpoints", "__pycache__"}
NUM = re.compile(r"-?\d+\.\d+")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--rename-map", type=Path, required=True)
    ap.add_argument("--search", action="append", default=[], help="subfolder(s) to search (default: whole project)")
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--min-score", type=float, default=0.5)
    ap.add_argument("--max-size-mb", type=float, default=5)
    ap.add_argument("--update", action="store_true")
    args = ap.parse_args()

    root = args.project_root.resolve()
    rm = json.loads(args.rename_map.read_text())
    inline = [e for e in rm["entries"] if (e["status"] == "inline" or e.get("table_file") == "full")
              and e.get("fingerprint")]
    if not inline:
        print("No inline tables with fingerprints in the rename map.")
        return

    cands = []
    bases = [root / s for s in args.search] or [root]
    for b in bases:
        for dp, dns, fns in os.walk(b):
            dns[:] = [d for d in dns if d not in SKIP and not any(x in os.path.join(dp, d) for x in args.exclude)]
            for f in fns:
                p = Path(dp) / f
                if p.suffix.lower() not in EXTS:
                    continue
                try:
                    if p.stat().st_size > args.max_size_mb * 1e6:
                        continue
                    txt = read_text_retry(p)
                except OSError:
                    continue
                if "\\documentclass" in txt:
                    continue
                nums = set(NUM.findall(txt))
                if len(nums) >= 3:
                    cands.append((os.path.relpath(p, root), nums, p.stat().st_mtime))
    print(f"Searched {len(cands)} candidate files\n")

    for e in inline:
        fp = set(e["fingerprint"])
        scored = []
        for path, nums, mt in cands:
            inter = len(fp & nums)
            if inter:
                scored.append((inter / len(fp), inter / len(nums), mt, path))
        scored.sort(key=lambda x: (-round(x[0], 2), -x[1], -x[2]))
        print(f"{e['name']}  ({e.get('label') or e.get('caption', '')[:60]})  — {len(fp)} numbers")
        for s, prec, _, path in scored[:3]:
            print(f"    {s:5.2f} recall  {prec:5.2f} precision  {path}")
        pair = None
        if scored and scored[0][0] < 0.85:
            top = scored[:12]
            nums = {path: n for path, n, _ in cands}
            for i in range(len(top)):
                for j in range(i + 1, len(top)):
                    a, b = top[i][3], top[j][3]
                    r = len(fp & (nums[a] | nums[b])) / len(fp)
                    if r >= scored[0][0] + 0.25 and (pair is None or r > pair[0]):
                        pair = (r, a, b)
            if pair:
                print(f"    {pair[0]:5.2f} recall  as panels: {pair[1]}  +  {pair[2]}")
        if e.get("hint"):
            print(f"    hint in .tex comments (may be stale): {'; '.join(e['hint'])}")
        if not scored:
            print("    no match — the table may be hand-made or produced as a log; ask the user")
        if e.get("table_file") == "full":
            # complete table file referenced by the paper: look for the code output it was edited from
            own = e["sources"][0]
            others = [x for x in scored if x[3] != own and x[1] >= 0.3]   # recall first, but not a huge unrelated file
            if args.update and others and others[0][0] >= args.min_score:
                e["generator"], e["generator_score"] = others[0][3], round(others[0][0], 2)
            print(f"    (complete table file referenced by the paper: {own}; best other candidate = likely code output)")
        elif args.update and pair and pair[0] >= args.min_score:
            e["matched_source"] = pair[1]
            e["matched_panels"] = [pair[1], pair[2]]
            e["match_score"] = round(pair[0], 2)
            e["sources"] = [pair[1], pair[2]]
        elif args.update and scored and scored[0][0] >= args.min_score:
            e["matched_source"] = scored[0][3]
            e["match_score"] = round(scored[0][0], 2)
            e["sources"] = [scored[0][3]]
        print()

    if args.update:
        assert_writable(args.rename_map, [root])
        args.rename_map.write_text(json.dumps(rm, indent=2, ensure_ascii=False))
        print(f"✅ Updated {args.rename_map}")


if __name__ == "__main__":
    main()
