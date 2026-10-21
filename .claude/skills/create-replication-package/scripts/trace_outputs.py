#!/usr/bin/env python3
"""
Trace every paper figure/table back to the code that produces it, and that code back to
the data it needs. Source folders are usually messy (several papers, abandoned versions,
co-author copies), so the replication package should contain only the code on these paths.

Usage:
    python trace_outputs.py --project-root <source> --rename-map rename_map.json \
        [--exclude unused --exclude old] [--extra-root <other dir with code>] \
        --output lineage.json --report lineage.md

How it works (heuristic — always review the report):
  1. Index all code files (.py .ipy .ipynb .do .ado .R .Rmd .m .jl .sh .sbatch).
     For notebooks only code cells are read.
  2. For each output in the rename map, find producers:
       exact   the output's file stem appears in the code, on a line that writes
       partial string literals in the code cover >=60% of the stem (names built from
               pieces like 'Msimulations_regs_' + var + '_small')
  3. For each producer, collect data files it reads/writes (string literals with data
     extensions; Stata use/merge/append/save without quotes), and scripts it calls
     (do/run/include, %run, source(), local imports).
  4. Walk upstream: a file read by a needed script and written by another script makes
     that script needed too. Files read but written by no script are raw inputs; their
     on-disk locations are looked up by basename.
Outputs a JSON lineage and a Markdown report with: producers per output, needed scripts in
dependency order, raw inputs with locations/sizes, unresolved outputs, and dynamic names.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry, probe  # noqa: E402

CODE_EXT = {".py": "python", ".ipy": "python", ".ipynb": "notebook", ".do": "stata", ".ado": "stata",
            ".r": "r", ".rmd": "r", ".m": "matlab", ".jl": "julia", ".sh": "shell", ".sbatch": "shell"}
DATA_EXT = ("dta|csv|tsv|xlsx?|xls|shp|geojson|gpkg|gdb|parquet|pkl|pickle|feather|rds|rdata|"
            "tif|tiff|nc|json|txt|zip|gz|7z|sav|sas7bdat|dbf|npy|npz|h5|hdf5|mat|ster|gml|kml")
RE_DATA_LIT = re.compile(r"""['"]([^'"\n]{1,300}?\.(?:%s))['"]""" % DATA_EXT, re.I)
RE_STATA_IO = re.compile(
    r"""^\s*(?:qui(?:etly)?\s+|cap(?:ture)?\s+|noi(?:sily)?\s+)*"""
    r"""(use|save|saveold|merge\s+\S+\s+[^,]*?\s+using|append\s+using|joinby\s+[^,]*?using|"""
    r"""cross\s+using|import\s+(?:delimited|excel)(?:\s+using)?|insheet\s+using|export\s+(?:delimited|excel)(?:\s+using)?|"""
    r"""outsheet\s+(?:[^,]*?\s)?using|shp2dta\s+using|spshape2dta)\s+"?([^",\s]+)""", re.I | re.M)
RE_STR = re.compile(r"""(?:'([^'\n]{3,200})'|"([^"\n]{3,200})")""")
RE_CALLS = re.compile(
    r"""(?:^\s*(?:do|run|include)\s+"?([^"\s,]+?(?:\.do)?)"?\s*$)"""      # Stata do/run/include
    r"""|(?:%run\s+["']?([^\s"']+))"""                                       # IPython %run
    r"""|(?:source\(\s*["']([^"']+)["'])"""                                  # R source()
    r"""|(?:jupyter\s+nbconvert[^\n]*?["']?([\w./-]+\.ipynb))"""            # nbconvert
    r"""|(?:python\s+([\w./-]+\.py))""", re.M | re.I)
WRITE_HINT = re.compile(
    r"savefig|to_csv|to_stata|to_file|to_excel|to_parquet|to_pickle|to_latex|to_json|to_feather|"
    r"\.save\(|np\.save|dump\(|write|export|esttab|estout|outreg|graph\s+export|texsave|putexcel|"
    r"\bsave\b|saveold|outsheet|ggsave|saveRDS|pdf\(|png\(|stargazer|etable|tikz|print\(.*file", re.I)
SKIP_DIRS = {".git", ".ipynb_checkpoints", "__pycache__", "node_modules", ".Trash", ".virtual_documents"}


def read_code(path: Path):
    try:
        if path.suffix.lower() == ".ipynb":
            nb = json.loads(read_text_retry(path))
            cells = nb.get("cells", [])
            src = "\n".join("".join(c.get("source", "")) if isinstance(c.get("source"), list) else c.get("source", "")
                            for c in cells if c.get("cell_type") == "code")
            k = nb.get("metadata", {}).get("kernelspec", {}).get("name", "")
            lang = "stata" if ("stata" in k or "%%stata" in src) else ("r" if k in ("ir", "r") else "python")
            return src, lang
        return read_text_retry(path), CODE_EXT[path.suffix.lower()]
    except (OSError, ValueError) as e:
        return None, str(e)


def walk(root: Path, excludes):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not any(x in os.path.join(dp, d) for x in excludes)]
        for f in fns:
            yield Path(dp) / f


def file_io(text: str, lang: str):
    reads, writes = set(), set()
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("//") or (lang == "stata" and s.startswith("*")) or \
                (lang in ("python", "r", "shell", "julia") and s.startswith("#")) or (lang == "matlab" and s.startswith("%")):
            continue
        w =bool(WRITE_HINT.search(ln))
        for m in RE_DATA_LIT.finditer(ln):
            (writes if w else reads).add(os.path.basename(m.group(1).replace("\\", "/")))
        if lang == "stata":
            for m in RE_STATA_IO.finditer(ln):
                verb, f = m.group(1).lower(), m.group(2)
                if "`" in f or "$" in f:
                    continue
                f = os.path.basename(f.replace("\\", "/"))
                if not re.search(r"\.\w{2,5}$", f):
                    f += ".dta" if not verb.startswith(("import", "insheet", "export", "outsheet")) else ""
                (writes if verb.startswith(("save", "export", "outsheet")) else reads).add(f)
    return reads, writes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--extra-root", type=Path, action="append", default=[],
                    help="additional folders with code/data (e.g. a shared co-author folder)")
    ap.add_argument("--rename-map", type=Path, help="output of parse_latex.py")
    ap.add_argument("--targets", nargs="*", default=[], help="extra output file names to trace")
    ap.add_argument("--exclude", action="append", default=[], help="path substring to skip (repeatable)")
    ap.add_argument("--min-coverage", type=float, default=0.6)
    ap.add_argument("--max-writers", type=int, default=2,
                    help="if more scripts than this write the same file name, do not follow it automatically")
    ap.add_argument("--output", type=Path, default=Path("lineage.json"))
    ap.add_argument("--report", type=Path, default=Path("lineage.md"))
    args = ap.parse_args()
    roots = [args.project_root.resolve()] + [r.resolve() for r in args.extra_root]
    base = roots[0]

    def rel(p):
        return os.path.relpath(p, base)

    # ---- index files ----
    code, unreadable, by_name = {}, [], defaultdict(list)
    for r in roots:
        for p in walk(r, args.exclude):
            by_name[p.name.lower()].append(p)
            if p.suffix.lower() in CODE_EXT:
                txt, lang = read_code(p)
                if txt is None:
                    unreadable.append((rel(p), lang))
                    continue
                lits = set(a or b for a, b in RE_STR.findall(txt))
                rd, wr = file_io(txt, lang)
                calls = set()
                for m in RE_CALLS.finditer(txt):
                    c = next((g for g in m.groups() if g), None)
                    if c:
                        calls.add(os.path.basename(c))
                try:
                    mt = p.stat().st_mtime
                except OSError:
                    mt = 0
                code[rel(p)] = {"lang": lang, "text": txt, "lits": lits, "reads": rd, "writes": wr,
                                "calls": calls, "mtime": mt}
    print(f"Indexed {len(code)} code files ({len(unreadable)} unreadable)", file=sys.stderr)

    # ---- targets ----
    targets = []
    if args.rename_map:
        rm = json.loads(args.rename_map.read_text())
        for e in rm["entries"]:
            if e["status"] in ("duplicate",):
                continue
            names = [os.path.basename(s) for s in e.get("sources", [])] or \
                    ([os.path.basename(e["latex_path"])] if e.get("latex_path") else []) or \
                    [os.path.basename(h) for h in e.get("hint", [])]
            targets.append({"name": e["name"], "files": names, "status": e["status"]})
    for t in args.targets:
        targets.append({"name": t, "files": [t], "status": "manual"})

    # ---- producers ----
    def producers(fname):
        stem = re.sub(r"\.\w{2,5}$", "", fname)
        exact, partial = [], []
        if len(stem) < 3:
            return exact, partial
        for path, c in code.items():
            txt = c["text"]
            if stem in txt:
                lines = [ln for ln in txt.splitlines() if stem in ln]
                if any(WRITE_HINT.search(ln) for ln in lines) or c["lang"] == "stata":
                    exact.append(path)
                    continue
            covered = [False] * len(stem)
            for lit in c["lits"]:
                if len(lit) >= 4:
                    i = stem.find(lit)
                    while i != -1:
                        for k in range(i, i + len(lit)):
                            covered[k] = True
                        i = stem.find(lit, i + 1)
            cov = sum(covered) / len(stem)
            if cov >= args.min_coverage and WRITE_HINT.search(txt):
                partial.append((path, round(cov, 2)))
        # best coverage first; among near-ties the most recently modified file first
        partial.sort(key=lambda x: (-round(x[1] / 0.03), -code[x[0]]["mtime"]))
        exact.sort(key=lambda x: -code[x]["mtime"])
        return exact, partial[:5]

    out_map, needed, unresolved = [], set(), []
    for t in targets:
        rec = {"name": t["name"], "files": t["files"], "exact": [], "partial": []}
        for f in t["files"]:
            ex, pa = producers(f)
            rec["exact"] += [x for x in ex if x not in rec["exact"]]
            rec["partial"] += [x for x in pa if x[0] not in [y[0] for y in rec["partial"]]]
        if rec["exact"]:
            needed.update(rec["exact"])
        elif rec["partial"]:
            needed.add(rec["partial"][0][0])
        else:
            unresolved.append(t["name"])
        out_map.append(rec)

    # ---- upstream walk ----
    writers = defaultdict(set)
    for path, c in code.items():
        for w in c["writes"]:
            writers[w.lower()].add(path)
    code_by_base = defaultdict(list)
    for path in code:
        code_by_base[os.path.basename(path).lower()].append(path)

    edges, frontier, raw_inputs = defaultdict(set), list(needed), defaultdict(set)
    ambiguous = defaultdict(set)
    while frontier:
        s = frontier.pop()
        c = code[s]
        for called in c["calls"]:
            for cand in code_by_base.get(called.lower(), []) + code_by_base.get((called + ".do").lower(), []):
                edges[s].add(cand)
                if cand not in needed:
                    needed.add(cand)
                    frontier.append(cand)
        for f in c["reads"]:
            ws = writers.get(f.lower(), set()) - {s}
            if len(ws) > args.max_writers:
                ambiguous[f].update(ws)
                continue
            if ws:
                for w in ws:
                    edges[s].add(w)
                    if w not in needed:
                        needed.add(w)
                        frontier.append(w)
            elif f.lower() not in {x.lower() for x in c["writes"]}:
                raw_inputs[f].add(s)

    # topological order (upstream first)
    order, seen = [], set()

    def visit(n, stack=()):
        if n in seen or n in stack:
            return
        for m in sorted(edges.get(n, ())):
            visit(m, stack + (n,))
        seen.add(n)
        order.append(n)
    for n in sorted(needed):
        visit(n)

    raw = []
    for f, users in sorted(raw_inputs.items()):
        locs = by_name.get(f.lower(), [])
        size = sum(p.stat().st_size for p in locs[:1] if p.exists()) if locs else 0
        raw.append({"file": f, "used_by": sorted(users), "found": [rel(p) for p in locs[:5]],
                    "n_found": len(locs), "size_mb": round(size / 1e6, 1)})

    dynamic = {}
    for s in needed:
        dyn = [ln.strip()[:160] for ln in code[s]["text"].splitlines()
               if re.search(r"(f['\"].*\{.*\}.*\.(%s))|(`[^']+'.*\.(%s))|(\+\s*['\"]\.(%s))" % (DATA_EXT, DATA_EXT, DATA_EXT), ln, re.I)]
        if dyn:
            dynamic[s] = dyn[:8]

    result = {"project_root": str(base), "outputs": out_map, "needed_scripts": order,
              "edges": {k: sorted(v) for k, v in edges.items()}, "raw_inputs": raw,
              "unresolved_outputs": unresolved,
              "ambiguous_inputs": {k: sorted(v) for k, v in ambiguous.items()}, "dynamic_paths": dynamic,
              "unreadable": unreadable, "n_code_files": len(code)}
    assert_writable(args.output, roots)
    assert_writable(args.report, roots)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # ---- report ----
    L = [f"# Lineage report for `{base.name}`", "",
         f"Indexed {len(code)} code files; **{len(order)} are needed** for the paper outputs.", ""]
    if unreadable:
        L += ["## ⚠️ Unreadable files (online-only files that could not be downloaded from here — trigger the download through the host and re-run; see SKILL.md)", ""]
        L += [f"- `{p}` ({err})" for p, err in unreadable[:50]] + [""]
    L += ["## Outputs → producing code", "", "| Output | File(s) | Exact producer(s) | Partial match (coverage) |",
          "|---|---|---|---|"]
    for r in out_map:
        L.append(f"| {r['name']} | {', '.join(r['files'][:2])} | {'<br>'.join(r['exact'][:4]) or '—'} | "
                 f"{'<br>'.join(f'{p} ({c})' for p, c in r['partial'][:3]) or '—'} |")
    L += ["", "## Needed scripts in dependency order (upstream first)", ""]
    for i, s in enumerate(order, 1):
        deps = ", ".join(f"`{d}`" for d in sorted(edges.get(s, ()))) or "—"
        L.append(f"{i}. `{s}` ({code[s]['lang']}) ← {deps}")
    L += ["", "## Raw inputs (read but never written by any script)", "",
          "| File | Found at | Size (MB) | Used by |", "|---|---|---|---|"]
    for r in raw:
        found = "<br>".join(r["found"][:3]) + (f" (+{r['n_found'] - 3})" if r["n_found"] > 3 else "") if r["found"] else "**NOT FOUND**"
        L.append(f"| {r['file']} | {found} | {r['size_mb']} | {', '.join(r['used_by'][:3])} |")
    if ambiguous:
        L += ["", f"## Ambiguous inputs (written by more than {args.max_writers} scripts — not followed; pick the right writer)", ""]
        for f, ws in sorted(ambiguous.items()):
            L.append(f"- `{f}` ← " + ", ".join(f"`{w}`" for w in sorted(ws, key=lambda w: -code[w]['mtime'])[:6]))
    if unresolved:
        L += ["", "## Unresolved outputs (no producer found — ask the user)", ""] + [f"- {u}" for u in unresolved]
    if dynamic:
        L += ["", "## Dynamically built paths (check by hand)", ""]
        for s, lines in dynamic.items():
            L.append(f"- `{s}`")
            L += [f"    - `{x}`" for x in lines]
    args.report.write_text("\n".join(L) + "\n")
    print(f"✅ {len(order)} needed scripts, {len(raw)} raw inputs, {len(unresolved)} unresolved outputs")
    print(f"   JSON: {args.output}\n   Report: {args.report}")


if __name__ == "__main__":
    main()
