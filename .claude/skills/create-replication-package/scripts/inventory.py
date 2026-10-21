#!/usr/bin/env python3
"""
Read-only inventory of a messy research folder — the first thing to run (Phase 1).

Usage:
    python inventory.py <source-folder> [--extra <other folder> ...] [--output inventory.md] [--json inventory.json]

Reports:
  * candidate paper .tex files (has \\documentclass), newest first, with #figures,
    #\\input, \\appendix presence and title — to pick the FINAL version with the user
  * manuscript IDs found in file names (e.g. MS20230792 from editor letters)
  * code files by language and folder (and notebooks' kernels)
  * data folders with sizes; files > 1 GB
  * cloud-only / unreadable files (Dropbox/Drive "online only" -> errno 35 / EDEADLK)
  * environment files (environment.yml, requirements.txt, renv.lock, *.pkl adolist)
  * earlier replication attempts (folders whose name contains "replication")
  * absolute paths / foreign machines referenced in code (summary; use audit_paths.py for detail)
"""
import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry, probe  # noqa: E402

CODE = {".py": "Python", ".ipy": "Python", ".ipynb": "Notebook", ".do": "Stata", ".ado": "Stata", ".r": "R",
        ".rmd": "R", ".m": "Matlab", ".jl": "Julia", ".sh": "Shell", ".sbatch": "Shell/SLURM", ".slurm": "Shell/SLURM"}
DATA = {".dta", ".csv", ".tsv", ".xlsx", ".xls", ".shp", ".geojson", ".gpkg", ".parquet", ".pkl", ".feather",
        ".rds", ".rdata", ".tif", ".tiff", ".nc", ".sav", ".zip", ".gz", ".7z", ".json", ".dbf", ".npy", ".h5", ".mat"}
FIGS = {".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"}
SKIP = {".git", ".ipynb_checkpoints", "__pycache__", "node_modules", ".Trash", ".virtual_documents"}
ABS = re.compile(r"""['"](/Users/[^'"]+|/home/[^'"]+|/Volumes/[^'"]+|[A-Z]:\\\\[^'"]+|~/[^'"]+)['"]""")


def readable(p: Path):
    return probe(p)


def human(n):
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.0f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


def scan(root: Path):
    R = {"tex": [], "code": [], "data_dirs": defaultdict(lambda: [0, 0]), "big": [], "unreadable": [],
         "env": [], "replication_dirs": [], "ms_ids": Counter(), "abs_paths": Counter(), "figs": 0, "n": 0}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for d in dns:
            if "replication" in d.lower():
                R["replication_dirs"].append(os.path.relpath(os.path.join(dp, d), root))
        for f in fns:
            p = Path(dp) / f
            R["n"] += 1
            rel = os.path.relpath(p, root)
            ext = p.suffix.lower()
            for m in re.findall(r"\b(MS\d{6,}|[A-Z]{2,6}-\d{4}-\d{3,})\b", f):
                R["ms_ids"][m] += 1
            try:
                st = p.stat()
            except OSError:
                continue
            if st.st_size > 1e9:
                R["big"].append((rel, st.st_size))
            if f in ("environment.yml", "environment.yaml", "requirements.txt", "renv.lock", "Pipfile",
                     "pyproject.toml", "setup.do") or ext == ".pkl" and "ado" in f.lower():
                R["env"].append(rel)
            if ext in DATA:
                top = rel.split(os.sep)[0] if os.sep in rel else "."
                sub = os.sep.join(rel.split(os.sep)[:2]) if rel.count(os.sep) >= 2 else top
                R["data_dirs"][sub][0] += 1
                R["data_dirs"][sub][1] += st.st_size
            elif ext in FIGS:
                R["figs"] += 1
            if ext in CODE or ext == ".tex":
                ok, err = readable(p)
                if not ok:
                    R["unreadable"].append((rel, err))
                    continue
                txt = read_text_retry(p) if st.st_size < 20e6 else ""
                if ext == ".tex":
                    if "\\documentclass" in txt:
                        t = re.search(r"\\title\s*(?:\[[^\]]*\])?\{([^}]*)", txt)
                        R["tex"].append({"file": rel, "mtime": st.st_mtime, "size": st.st_size,
                                         "graphics": len(re.findall(r"^[^%\n]*\\includegraphics", txt, re.M)),
                                         "inputs": len(re.findall(r"^[^%\n]*\\input\{", txt, re.M)),
                                         "tables": len(re.findall(r"^[^%\n]*\\begin\{table", txt, re.M)),
                                         "appendix": bool(re.search(r"^[^%\n]*\\appendix", txt, re.M)),
                                         "title": re.sub(r"\s+", " ", t.group(1)).strip()[:80] if t else ""})
                    continue
                kernel = ""
                if ext == ".ipynb":
                    try:
                        kernel = json.loads(txt).get("metadata", {}).get("kernelspec", {}).get("name", "")
                    except ValueError:
                        pass
                for m in ABS.findall(txt):
                    parts = m.split("/")
                    R["abs_paths"]["/".join(parts[:3]) if m.startswith("/") else m[:20]] += 1
                R["code"].append({"file": rel, "lang": CODE[ext], "kernel": kernel, "mtime": st.st_mtime,
                                  "lines": txt.count("\n")})
    return R


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("--extra", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--hydrate-list", type=Path, default=None,
                    help="write absolute paths of online-only files this environment could not download (one per line)")
    args = ap.parse_args()

    L, allR = [], {}
    for root in [args.source] + args.extra:
        root = root.resolve()
        R = scan(root)
        allR[str(root)] = R
        L += [f"# Inventory of `{root}`", "", f"{R['n']} files, {len(R['code'])} code files, {R['figs']} figure files.", ""]
        if R["ms_ids"]:
            L += ["**Manuscript IDs seen in file names:** " + ", ".join(f"{k} ({v})" for k, v in R["ms_ids"].most_common(5)), ""]
        L += ["## Candidate paper sources (newest first) — confirm the FINAL one with the user", "",
              "| .tex | modified | figs | \\input | tables | \\appendix | title |", "|---|---|---|---|---|---|---|"]
        for t in sorted(R["tex"], key=lambda x: -x["mtime"])[:25]:
            L.append(f"| {t['file']} | {time.strftime('%Y-%m-%d', time.localtime(t['mtime']))} | {t['graphics']} | "
                     f"{t['inputs']} | {t['tables']} | {'yes' if t['appendix'] else ''} | {t['title']} |")
        L += ["", "## Code by folder and language", ""]
        byf = defaultdict(Counter)
        for c in R["code"]:
            byf[os.path.dirname(c["file"]) or "."][c["lang"] + (f" [{c['kernel']}]" if c["kernel"] else "")] += 1
        for d, cnt in sorted(byf.items()):
            L.append(f"- `{d}/`: " + ", ".join(f"{k} × {v}" for k, v in cnt.most_common()))
        L += ["", "## Data folders (by size)", "", "| folder | files | size |", "|---|---|---|"]
        for d, (n, s) in sorted(R["data_dirs"].items(), key=lambda x: -x[1][1])[:30]:
            L.append(f"| {d} | {n} | {human(s)} |")
        if R["big"]:
            L += ["", "## Files over 1 GB (consider scratch_data/, compression, or external hosting)", ""]
            L += [f"- `{f}` — {human(s)}" for f, s in sorted(R["big"], key=lambda x: -x[1])[:20]]
        if R["env"]:
            L += ["", "## Environment / package files", ""] + [f"- `{e}`" for e in R["env"]]
        if R["replication_dirs"]:
            L += ["", "## Earlier replication attempts (reuse what is good; never overwrite)", ""] + \
                 [f"- `{d}`" for d in R["replication_dirs"]]
        if R["abs_paths"]:
            L += ["", "## Absolute paths referenced in code (other machines/drives — must be made relative)", ""]
            L += [f"- `{k}` × {v}" for k, v in R["abs_paths"].most_common(15)]
        if R["unreadable"]:
            L += ["", f"## ⚠️ {len(R['unreadable'])} code/tex files could not be downloaded from here",
                  "Cloud 'online-only' files (Dropbox/Google Drive). On the user's own Mac they download when opened; "
                  "inside a sandbox/VM the cloud provider may not respond. Trigger the download through the host "
                  "(see SKILL.md, 'Online-only files') and re-run — do not ask the user to do it.", ""]
            L += [f"- `{f}` {e}" for f, e in R["unreadable"][:30]]
            if len(R["unreadable"]) > 30:
                L.append(f"- … and {len(R['unreadable']) - 30} more")
        L.append("")

    if args.hydrate_list:
        assert_writable(args.hydrate_list, [args.source] + args.extra)
        home = str(Path.home())
        # "~/..." spelling so the paths can be handed to a host-side tool (e.g. Cowork's device_stage_files)
        paths = [str(Path(root) / f).replace(home, "~", 1) for root, R in allR.items() for f, _ in R["unreadable"]]
        args.hydrate_list.write_text("\n".join(paths) + ("\n" if paths else ""))
        print(f"{len(paths)} online-only file(s) listed in {args.hydrate_list}")
    text = "\n".join(L)
    if args.output:
        assert_writable(args.output, [args.source] + args.extra)
        args.output.write_text(text)
        print(f"✅ Inventory written to {args.output}")
    else:
        print(text)
    if args.json:
        ser = {k: {kk: (dict(vv) if isinstance(vv, (Counter, defaultdict)) else vv) for kk, vv in v.items()}
               for k, v in allR.items()}
        assert_writable(args.json, [args.source] + args.extra)
        args.json.write_text(json.dumps(ser, indent=2, default=str))


if __name__ == "__main__":
    main()
