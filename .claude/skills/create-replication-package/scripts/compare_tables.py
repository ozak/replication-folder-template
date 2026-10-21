#!/usr/bin/env python3
"""
Check that the regenerated tables reproduce the numbers in the final paper.

Usage:
    python compare_tables.py <target>                      # uses <target>/_migration/original_bodies
    python compare_tables.py <target> --rename-map <target>/_migration/rename_map.json   # also \\input-ed tables

For each table it compares the reference (the body rows that were pasted in the final .tex,
saved by rewrite_tex_paths.py, or the original \\input file from the source project) with the
file the package produces in replication-package/tables/(paper|appendix)/:

  numbers  every number, in order (stars, parentheses, brackets, commas ignored).
           Must match exactly as printed — any difference means the code does not reproduce
           the paper (wrong version of a script, data vintage, sample, seed...). Never "fix" it by
           editing numbers; find the cause.
  labels   row labels (first cell). Differences are presentation edits made in the paper after
           the code ran. Add them to the `replace=[(generated, final), ...]` list of the table's
           extract_body()/wrap_table() call in Renaming.ipynb (suggestions are printed).
  rows     rows are aligned by their numbers. Rows the code produces but the paper omits (e.g. a
           "Mean Dependent" row commented out in the paper) go into drop_rows=[...]; rows in the
           paper that the code does not produce are errors.

Exit code 1 if any table's numbers differ.
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry, probe  # noqa: E402

NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?:e[-+]?\d+)?(?![\w])")


def body_of(text):
    text = re.sub(r"(?<!\\)%[^\n]*", "", text)
    if "\\begin{tabular" in text or "\\bottomrule" in text:
        m = re.search(r"\\midrule[^\n]*\n", text)
        if m:
            b = text.find("\\bottomrule", m.end())
            text = text[m.end(): b if b != -1 else len(text)]
    return text


def rows_of(text):
    out = []
    for raw in re.split(r"\\\\(?:\[[^\]]*\])?", body_of(text)):
        r = re.sub(r"\\(?:midrule|toprule|bottomrule|hline|addlinespace)\b(?:\[[^\]]*\])?|\\cmidrule(?:\([^)]*\))?\{[^}]*\}", "", raw).strip()
        if not r:
            continue
        cells = re.split(r"(?<!\\)&", r)
        label = re.sub(r"\s+", " ", cells[0]).strip()
        nums = [n.replace(",", "") for c in cells[1:] for n in NUM.findall(re.sub(r"\\sym\{[^}]*\}|\^\{?\*+\}?", "", c))]
        out.append((label, nums))
    return out


def compare(ref_text, gen_text):
    """Align rows by their numbers (difflib) so dropped/added rows do not cascade."""
    ref = [(l, tuple(n)) for l, n in rows_of(ref_text) if n]
    gen = [(l, tuple(n)) for l, n in rows_of(gen_text) if n]
    res = {"n_ref": sum(len(n) for _, n in ref), "n_gen": sum(len(n) for _, n in gen),
           "diffs": [], "labels": [], "dropped": [], "missing": []}
    sm = difflib.SequenceMatcher(a=[n for _, n in gen], b=[n for _, n in ref], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for (gl, _), (rl, _) in zip(gen[i1:i2], ref[j1:j2]):
                if gl != rl:
                    res["labels"].append((gl, rl))
        elif op == "delete":
            res["dropped"] += [gl for gl, _ in gen[i1:i2]]
        elif op == "insert":
            res["missing"] += [rl for rl, _ in ref[j1:j2]]
        else:  # replace: same position, different numbers
            for (gl, gn), (rl, rn) in zip(gen[i1:i2], ref[j1:j2]):
                res["diffs"].append((rl, " ".join(rn), " ".join(gn)))
            if i2 - i1 > j2 - j1:
                res["dropped"] += [gl for gl, _ in gen[i1 + (j2 - j1):i2]]
            elif j2 - j1 > i2 - i1:
                res["missing"] += [rl for rl, _ in ref[j1 + (i2 - i1):j2]]
    res["numbers_ok"] = not res["diffs"] and not res["missing"]
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", type=Path)
    ap.add_argument("--original-bodies", type=Path, default=None)
    ap.add_argument("--rename-map", type=Path, default=None)
    a = ap.parse_args()
    P = a.target / "replication-package"
    pairs = []
    ob = a.original_bodies or a.target / "_migration" / "original_bodies"
    if ob.is_dir():
        for f in sorted(ob.glob("*.tex")):
            gens = [P / "tables" / loc / f.name for loc in ("paper", "appendix")]
            pairs.append((f.stem, f, next((g for g in gens if g.exists()), gens[0])))
    if a.rename_map:
        rm = json.loads(a.rename_map.read_text())
        root = Path(rm["project_root"])
        done = {n for n, _, _ in pairs}
        for e in rm["entries"]:
            if e["kind"] == "table" and e["status"] == "ok" and e.get("sources") and e["name"] not in done:
                pairs.append((e["name"], root / e["sources"][0], P / e["dest"][0]))
    if not pairs:
        sys.exit("nothing to compare: no original_bodies/ and no --rename-map")

    bad = 0
    for name, ref, gen in pairs:
        if not gen.exists():
            print(f"❌ {name}: not generated yet (expected in replication-package/tables/paper|appendix/{gen.name})")
            bad += 1
            continue
        try:
            r = compare(read_text_retry(ref), read_text_retry(gen))
        except OSError as err:
            print(f"⚠️  {name}: cannot read reference {ref}: {err}")
            continue
        if r["numbers_ok"]:
            msg = f"✅ {name}: every number in the paper is reproduced ({r['n_ref']} numbers)"
        else:
            bad += 1
            msg = f"❌ {name}: numbers differ (paper {r['n_ref']}, code {r['n_gen']})"
            for lab, x, y in r["diffs"][:6]:
                msg += f"\n      row '{lab[:45]}':\n         paper {x[:90]}\n         code  {y[:90]}"
            for lab in r["missing"][:6]:
                msg += f"\n      row in the paper not produced by the code: '{lab[:60]}'"
        if r["dropped"]:
            msg += "\n   rows the code produces but the paper omits → drop_rows=[...]:\n      " + \
                   ", ".join(repr(x[:40]) for x in dict.fromkeys(r["dropped"]))
        if r["labels"]:
            msg += "\n   labels edited in the paper → replace=[...]:"
            for x, y in r["labels"][:10]:
                msg += f"\n      ({x!r}, {y!r}),"
        print(msg)
    print(f"\n{len(pairs)} table(s) compared, {bad} with problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
