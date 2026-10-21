#!/usr/bin/env python3
"""
Static checks on a finished (or in-progress) replication package. Run before telling the
user the package is done, and again after every round of fixes.

Usage:
    python check_package.py <target-folder>       # folder containing 1-paper/, 2-appendix/, replication-package/

Checks (❌ = must fix, ⚠️ = review):
  1. template placeholders left (XXX, TITLE, AWESOME, {{token}}, PASTE HERE ...)
  2. template artifacts left (CLAUDE.md, *.code-workspace, Stata-Notebook.ipynb, placeholder .tex)
  3. every \\includegraphics / \\input / \\inputbody in 1-paper/ and 2-appendix/ resolves to the flat
     graphs/ or tables/ folder next to the .tex, and the file exists in
     replication-package/graphs|tables/(paper|appendix)/ (Copy-Final source)
  4. final file names follow the convention (paper/ = numbers only, appendix/ = letter+number)
  5. every notebook in progs/ is run by index.ipynb, and index.ipynb runs nothing missing
  6. Stata notebooks: %%stata cells need `import stata_init` first and a python3 kernel
  7. absolute paths / cd in code
  8. README.md has the Data Editors sections; replication-zip.ipynb has exclusion rules
  9. environments: names match create_env.sh; no r-* packages in environment.yml; no pinned system
     libraries; environment-R.yml when R is used; _migration/env-check.md (check_env.py) passed; files > 2 GB
 10. no spaces in any folder or file name of the package (spaces become "-")
"""
import json
import os
import re
import sys
from pathlib import Path

PLACEHOLDERS = re.compile(r"AWESOME|awesome-project|Awesome-Project|\bXXX\b|\bTITLE\b|FURTHER TITLE|PASTE HERE|\{\{\s*\w+\s*\}\}|Python-XXX|Stata-XXX")
NAME_RX = re.compile(r"^(Figure|Table)-([A-Z]?)(\d+)(-[a-z]\d*)?(-Panel-[A-Z])?(-cont\d*)?(-[a-z]\d*)?$")
GRAPHIC_EXTS = [".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"]
ABS = re.compile(r"""(['"]/Users/|['"]/home/|['"]/Volumes/|['"][A-Za-z]:\\|Dropbox/|Google Drive/|^\s*cd\s+["']?/|os\.chdir|setwd\()""")

results = []


def report(level, msg):
    results.append((level, msg))


def code_cells(nb):
    for c in nb.get("cells", []):
        if c.get("cell_type") == "code":
            yield c["source"] if isinstance(c["source"], str) else "".join(c["source"])


def load_nb(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        report("❌", f"cannot read notebook {p}: {e}")
        return {"cells": []}


def resolve(base: Path, ref: str, exts):
    p = base / ref
    if p.suffix.lower() in exts and p.is_file():
        return [p]
    stem_dir, stem = p.parent, p.name
    return [x for x in stem_dir.glob(stem + ".*") if x.suffix.lower() in exts] if stem_dir.is_dir() else []


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) == 2 else 2)
    T = Path(sys.argv[1]).resolve()
    P = T / "replication-package"
    if not P.is_dir():
        sys.exit(f"{P} not found")

    # 1. placeholders
    for f in [P / "README.md", P / "index.ipynb", P / "environment.yml", P / "create_env.sh", P / "setup.do",
              T / "replication-zip.ipynb"]:
        if f.exists():
            txt = f.read_text(encoding="utf-8", errors="replace")
            hits = sorted(set(PLACEHOLDERS.findall(txt)))
            if hits:
                report("❌", f"placeholders in {f.relative_to(T)}: {', '.join(hits[:8])}")
    # 2. artifacts
    for a in ["CLAUDE.md", "replication-folder-template.code-workspace", "replication-package/progs/Stata/Stata-Notebook.ipynb",
              "1-paper/main.tex", "2-appendix/appendix.tex"]:
        if (T / a).exists():
            report("⚠️", f"template artifact still present: {a}")

    # 3-4. LaTeX references
    for doc_dir in ["1-paper", "2-appendix"]:
        D = T / doc_dir
        texs = [t for t in D.glob("*.tex") if "\\documentclass" in t.read_text(encoding="utf-8", errors="replace")] if D.is_dir() else []
        if not texs:
            report("❌", f"no compilable .tex in {doc_dir}/")
        for t in texs:
            txt = re.sub(r"(?<!\\)%[^\n]*", "", t.read_text(encoding="utf-8", errors="replace"))
            refs = [("g", m) for m in re.findall(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", txt)] + \
                   [("t", m) for m in re.findall(r"\\input(?:body)?\s*\{([^}]+)\}", txt)]
            n_ok = 0
            for kind, ref in refs:
                ref = ref.strip()
                if kind == "t" and not re.search(r"tables?/", ref):
                    continue
                exts = GRAPHIC_EXTS if kind == "g" else [".tex"]
                hits = resolve(D, ref, exts)
                if not hits:
                    report("❌", f"{doc_dir}/{t.name}: missing {ref}")
                    continue
                n_ok += 1
                rel = os.path.relpath(hits[0], D)
                if not re.match(r"(graphs|tables)/[^/]+$", rel):
                    report("⚠️", f"{doc_dir}/{t.name}: {ref} is not in the flat graphs/ or tables/ folder next to the .tex")
                else:
                    folder, name = rel.split("/")
                    if not any((P / folder / loc / name).exists() for loc in ("paper", "appendix")):
                        report("⚠️", f"{doc_dir}/{rel} not in replication-package/{folder}/(paper|appendix)/ (Copy-Final copies from there)")
            report("✅", f"{doc_dir}/{t.name}: {n_ok} figure/table references resolve")
    for sub in ["graphs/paper", "graphs/appendix", "tables/paper", "tables/appendix"]:  # package keeps paper/appendix
        d = P / sub
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.name.startswith("."):
                continue
            m = NAME_RX.match(f.stem)
            if not m:
                report("⚠️", f"non-standard name: replication-package/{sub}/{f.name}")
            elif ("appendix" in sub) != bool(m.group(2)):
                report("⚠️", f"{sub}/{f.name}: {'appendix files need a section letter' if 'appendix' in sub else 'paper files should not have a letter'}")

    # 5-7. notebooks
    idx = P / "index.ipynb"
    run_names = set()
    if idx.exists():
        src = "\n".join(code_cells(load_nb(idx)))
        run_names |= set(re.findall(r"notebook_name\s*=\s*['\"]([^'\"]+)['\"]", src))
        run_names |= {Path(x).stem for x in re.findall(r"([\w./-]+\.ipynb)", src)}
        run_names |= {Path(x).stem for x in re.findall(r"([\w./-]+\.(?:do|py|R|sh|sbatch))", src)}
    else:
        report("❌", "replication-package/index.ipynb missing")
    progs = P / "progs"
    nbs = [p for p in progs.rglob("*.ipynb") if ".ipynb_checkpoints" not in p.parts and "unused" not in p.parts] if progs.is_dir() else []
    for nbp in nbs:
        if nbp.stem not in run_names:
            report("⚠️", f"not run by index.ipynb: {nbp.relative_to(P)}")
        nb = load_nb(nbp)
        cells = list(code_cells(nb))
        joined = "\n".join(cells)
        k = nb.get("metadata", {}).get("kernelspec", {}).get("name", "")
        if "%%stata" in joined:
            first = next((c for c in cells if c.strip()), "")
            if "import stata_init" not in first:
                report("❌", f"{nbp.relative_to(P)}: first code cell must be `import stata_init`")
            if k not in ("python3", "") and not k.startswith("conda-env"):
                report("⚠️", f"{nbp.relative_to(P)}: pystata notebook with kernel '{k}'")
        for ln in joined.splitlines():
            if ABS.search(ln) and not ln.strip().startswith(("#", "//", "*")):
                report("❌", f"{nbp.relative_to(P)}: non-portable path/cd: {ln.strip()[:100]}")
                break
    for name in sorted(run_names):
        if name and name != "stata_init" and name not in {p.stem for p in progs.rglob("*")} and not (P / name).exists() and "{" not in name:
            report("⚠️", f"index.ipynb references '{name}' but no such file in progs/")
    for p in progs.rglob("*") if progs.is_dir() else []:
        if p.suffix.lower() in (".do", ".py", ".r", ".ipy") and "unused" not in p.parts:
            for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if ABS.search(ln) and not ln.strip().startswith(("#", "//", "*")):
                    report("❌", f"{p.relative_to(P)}: non-portable path/cd: {ln.strip()[:100]}")
                    break

    # 8. README + zip
    rd = P / "README.md"
    if rd.exists():
        txt = rd.read_text(encoding="utf-8", errors="replace")
        for sec in ["Data Availability", "Computational requirements", "Description of programs", "Instructions to Replicators",
                    "List of tables", "References"]:
            if sec.lower() not in txt.lower():
                report("❌", f"README.md lacks section '{sec}'")
    else:
        report("❌", "replication-package/README.md missing")
    rz = T / "replication-zip.ipynb"
    if rz.exists():
        if "'include'] = False" not in rz.read_text(encoding="utf-8", errors="replace").replace('"include"', "'include'"):
            report("⚠️", "replication-zip.ipynb has no exclusion rule (add one, even a commented example)")
    else:
        report("❌", "replication-zip.ipynb missing")

    # 9. env + sizes
    env, renv, sh = P / "environment.yml", P / "environment-R.yml", P / "create_env.sh"
    sh_txt = sh.read_text() if sh.exists() else ""
    for f, var in ((env, "ENV_NAME"), (renv, "R_ENV_NAME")):
        if f.exists() and sh_txt:
            n1 = re.search(r"^name:\s*(\S+)", f.read_text(), re.M)
            n2 = re.search(rf'^{var}="?([^"\s]+)', sh_txt, re.M)
            if n1 and n2 and n1.group(1) != n2.group(1):
                report("❌", f"{f.name} name '{n1.group(1)}' != create_env.sh {var} '{n2.group(1)}'")
    sys_pin = re.compile(r"^\s*-\s*((?:lib\w*|openssl|curl|icu|zlib|openjdk|ca-certificates|tzdata|blas|mkl|openblas)[\w.-]*)=", re.M)
    for f in (env, renv):
        if f.exists():
            txt = f.read_text()
            pins = sys_pin.findall(txt)
            if pins:
                report("⚠️", f"{f.name}: system libraries pinned ({', '.join(pins[:6])}) — unpin them so the env resolves on every platform")
            if re.search(r"=\w+_\w+\s*$|=[\w.]+=[hp][0-9a-f]{6,}", txt, re.M):
                report("⚠️", f"{f.name}: build strings present — remove them (platform-specific)")
    if env.exists() and re.search(r"^\s*-\s*r-", env.read_text(), re.M):
        report("❌", "environment.yml contains r-* packages — R goes in environment-R.yml (separate env)")
    uses_r = progs.is_dir() and any(p.suffix.lower() in (".r", ".rmd") or (p.suffix == ".ipynb" and '"ir"' in p.read_text(errors="replace"))
                                    for p in progs.rglob("*") if p.is_file())
    if uses_r and not renv.exists():
        report("❌", "R code in progs/ but no environment-R.yml")
    chk = T / "_migration" / "env-check.md"
    if not chk.exists():
        report("⚠️", "no _migration/env-check.md — run check_env.py on the environment files (linux-64 + osx-arm64)")
    elif "❌" in chk.read_text():
        report("❌", "_migration/env-check.md reports environments that do not resolve")
    for dp, dns, fns in os.walk(P):
        for f in fns:
            fp = Path(dp) / f
            try:
                if fp.stat().st_size > 2e9:
                    report("⚠️", f"large file {fp.relative_to(P)} ({fp.stat().st_size / 1e9:.1f} GB) — compress, move to scratch_data/, or host externally")
            except OSError:
                pass

    # 10. no spaces in names
    spaced = []
    for dp, dns, fns in os.walk(T):
        dns[:] = [d for d in dns if d not in (".git", "_migration")]
        spaced += [Path(dp, n).relative_to(T) for n in dns + fns if re.search(r"\s", n)]
    for x in spaced[:20]:
        report("❌", f"space in name: {x} — rename with '-' and update every reference (code, .tex, index.ipynb)")
    if len(spaced) > 20:
        report("❌", f"... and {len(spaced) - 20} more names with spaces")

    order = {"❌": 0, "⚠️": 1, "✅": 2}
    for lvl, msg in sorted(results, key=lambda x: order[x[0]]):
        print(lvl, msg)
    n_err = sum(1 for l, _ in results if l == "❌")
    n_warn = sum(1 for l, _ in results if l == "⚠️")
    print(f"\n{n_err} error(s), {n_warn} warning(s)")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
