#!/usr/bin/env python3
"""
Generate progs/Python/Renaming.ipynb from the confirmed rename_map.json.

Each figure/table gets its own markdown header and an explicit copy cell, so a replicator
can see exactly which analysis output becomes which Figure-N / Table-N. Inline tables get a
wrap_table() cell to finish by hand (caption, column headers and notes come from the .tex).

Usage:
    python build_renaming_notebook.py --rename-map rename_map.json \
        --out <target>/replication-package/progs/Python/Renaming.ipynb \
        [--path-map '[["graphs/", "graphs/"], ["../graphs/", "graphs/"]]']

Sources in the rename map are relative to the *source project*. By default the migrated code
is assumed to write its outputs to the same relative location inside replication-package/
(e.g. source graphs/Jupyter/x.pdf -> replication-package/graphs/Jupyter/x.pdf). Use --path-map
(JSON list of [old_prefix, new_prefix]) when outputs moved.

Use this when the "Renaming notebook" strategy was chosen. With the "code writes final names"
strategy, generate it anyway: rows whose source already equals the destination are skipped.
"""
import argparse
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry, probe  # noqa: E402

HELPERS = r'''import os
import re
import shutil

PKG = "../../"   # notebook runs from progs/Python/

def copy_output(src, dst):
    """Copy an analysis output (relative to replication-package/) to its final name."""
    s, d = os.path.join(PKG, src), os.path.join(PKG, dst)
    if not os.path.exists(s):
        raise FileNotFoundError(f"{s} not found — run the notebook that produces it first")
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copyfile(s, d)
    print(f"{src}  ->  {dst}")

def wrap_table(src, dst, pre="", post="", body_between=None, replace=None, drop_rows=None):
    """Write dst = pre + body + post.
    body_between=(start_marker, end_marker) keeps only the lines strictly between the markers
    (e.g. (r"\midrule", r"\bottomrule") to keep the coefficient rows of an esttab file).
    replace: optional list of (old, new) string replacements applied to the body."""
    s, d = os.path.join(PKG, src), os.path.join(PKG, dst)
    with open(s, encoding="utf-8") as fh:
        body = fh.read()
    if body_between:
        a, b = body_between
        lines, keep, out = body.splitlines(), False, []
        for ln in lines:
            if ln.strip().startswith(b) and keep:
                break
            if keep:
                out.append(ln)
            if ln.strip().startswith(a) and not keep:
                keep = True
        body = "\n".join(out)
    if drop_rows:   # drop rows (lines) whose label starts with any of these strings
        body = "\n".join(ln for ln in body.splitlines() if not any(ln.strip().startswith(d) for d in drop_rows))
    for old, new in (replace or []):
        body = body.replace(old, new)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    with open(d, "w", encoding="utf-8") as fh:
        fh.write(pre + body + post)
    print(f"{src}  ->  {dst} (wrapped)")

def extract_body(src, dst, replace=None, drop_rows=None, start=r"\midrule", end=r"\bottomrule"):
    """Keep only the table BODY (rows between the header rule and the bottom rule).
    The paper keeps its own head (caption, column headers) and foot (notes) and \\input's this file,
    so numbers come from the code and presentation from the final paper.
    replace: (generated, final) pairs for row labels edited in the paper; drop_rows: labels of rows
    the paper omits (both suggested by compare_tables.py)."""
    wrap_table(src, dst, body_between=(start, end), replace=replace, drop_rows=drop_rows)
'''


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": t}


def code(t):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rename-map", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--path-map", default="[]")
    a = ap.parse_args()
    rm = json.loads(a.rename_map.read_text())
    pmap = json.loads(a.path_map)

    def remap(p):
        for old, new in pmap:
            if p.startswith(old):
                return new + p[len(old):]
        return p

    cells = [md("# Rename analysis outputs to final figure and table names\n\n"
                "Tables: only the **body** is produced here; captions, column headers and notes stay in the paper's .tex, "
                "so numbers come from the code and presentation from the final paper (`compare_tables.py` checks them).\n\n"
                "Copies each output produced by the analysis notebooks to `graphs/paper/`, `graphs/appendix/`, "
                "`tables/paper/` or `tables/appendix/` with its standardized name (`Figure-1-a`, `Table-D3`, ...). "
                "`Copy-Final.ipynb` then copies them next to the LaTeX sources in `1-paper/` and `2-appendix/`.\n\n"
                "*Generated from `rename_map.json`; edit freely.*"),
             code(HELPERS)]
    groups = {}
    for e in rm["entries"]:
        if e["status"] == "duplicate":
            continue
        base = re.match(r"((?:Figure|Table)-[A-Z]?\d+)", e["name"])
        groups.setdefault(base.group(1) if base else e["name"], []).append(e)

    for base, es in groups.items():
        cap = next((x["caption"] for x in es if x.get("caption")), "")
        lab = next((x["label"] for x in es if x.get("label")), "")
        head = f"## {base.replace('-', ' ', 1)}" + (f": {cap}" if cap else "") + (f"  \n`{lab}`" if lab else "")
        cells.append(md(head))
        lines = []
        for e in es:
            if e["status"] == "inline" and e.get("matched_panels"):
                d0 = e["dest"][0][:-4]
                lines.append(f"# {e['name']}: pasted table matched two generated files (panels, score {e.get('match_score')}).")
                lines.append("# In the .tex keep the panel header rows and \\input each panel body below.")
                for k, src in enumerate(e["matched_panels"]):
                    lines.append(f"extract_body({remap(src)!r}, {d0 + '-Panel-' + chr(65 + k) + '.tex'!r}, replace=[], drop_rows=[])")
            elif e["status"] == "inline":
                src = e.get("matched_source") or (e["hint"][0].lstrip("./") if e.get("hint") else "tables/TODO.tex")
                ok = bool(e.get("matched_source"))
                lines += [f"# {e['name']}: body pasted in the paper; head/foot stay in the .tex. Generated file: "
                          + (f"matched (score {e.get('match_score')})" if ok else "TODO — UNVERIFIED, confirm the source"),
                          f"extract_body({remap(src)!r}, {e['dest'][0]!r}, replace=[], drop_rows=[])  # fill from compare_tables.py"]
            elif e.get("table_file") == "full":
                src = e.get("generator") or e["sources"][0]
                lines += [f"# {e['name']}: the paper \\input'ed a complete (possibly hand-edited) table file; its head/foot now",
                          "# live in the .tex and only the body is generated here. Generator: "
                          + (f"{e['generator']} (matched, score {e.get('generator_score')})" if e.get("generator")
                             else "ASSUMED to be the referenced file itself — confirm the code writes it (lineage.md)"),
                          f"extract_body({remap(src)!r}, {e['dest'][0]!r}, replace=[], drop_rows=[])  # fill from compare_tables.py"]
            elif not e.get("sources"):
                lines.append(f"# TODO {e['name']}: source not found ({e.get('latex_path')}) — locate the output and add copy_output()")
            else:
                for s in e["sources"]:
                    ext = Path(s).suffix
                    dst = next((d for d in e["dest"] if d.endswith(ext)), e["dest"][0])
                    src = remap(s)
                    if src == dst:
                        continue
                    lines.append(f"copy_output({src!r}, {dst!r})")
        cells.append(code("\n".join(lines) if lines else "# nothing to rename (already final)"))

    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                       "language_info": {"name": "python"}},
          "cells": cells}
    assert_writable(a.out, [rm.get("project_root")])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    todo = sum(c["source"].count("TODO") for c in cells if c["cell_type"] == "code")
    print(f"✅ {a.out}: {len(groups)} figures/tables, {todo} TODO line(s) to finish by hand")


if __name__ == "__main__":
    main()
