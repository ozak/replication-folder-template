#!/usr/bin/env python3
"""
Convert Python (.py/.ipy), Stata (.do) or R (.R) scripts into Jupyter notebooks that follow
the template conventions. Logic is preserved — code is split into cells, never rewritten.

Usage:
    python convert_to_notebook.py --lang python  source.py   dest.ipynb [--source-label "progs/x.py"]
    python convert_to_notebook.py --lang stata   source.do   dest.ipynb
    python convert_to_notebook.py --lang r       source.R    dest.ipynb
    python convert_to_notebook.py --lang stata --stata-mode stata_kernel source.do dest.ipynb

Stata (default --stata-mode pystata, as in the template): the notebook uses the python3
kernel, its first code cell is `import stata_init` (index.ipynb writes progs/Stata/stata_init.py
with the replicator's Stata location), and every code cell starts with `%%stata`.
Files using `#delimit ;` are kept in a single cell. Locals persist across %%stata cells.

Cells are split at divider comments: `# ---`, `# ===`, `# %%`, `## Title`, `// ---`, `*****`,
`* ===`, `/* --- */`. The first comment block becomes the notebook description.
Notebooks run with the working directory = their own folder (progs/<Lang>/), so data paths
must be relative like ../../data/... — the converter lists suspicious paths at the end.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry, probe  # noqa: E402

KERNELS = {
    "python": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "stata_kernel": {"name": "stata", "display_name": "Stata", "language": "stata"},
    "r": {"name": "ir", "display_name": "R", "language": "R"},
}
DIVIDERS = {
    "python": re.compile(r"^\s*#\s*(?:%%.*|[-=*#]{3,}.*|#+\s+\S.*)$", re.M),
    "stata": re.compile(r"^\s*(?://\s*[-=*]{3,}.*|\*{3,}.*|\*\s*[-=]{3,}.*|/\*\s*[-=*]{3,}.*\*/)\s*$", re.M),
    "r": re.compile(r"^\s*#\s*(?:%%.*|[-=*#]{3,}.*|.*[-=#]{4,}\s*$)$", re.M),
}
SUSPECT_PATH = re.compile(r"""(/Users/|/home/|/Volumes/|[A-Z]:\\|~/|Dropbox|Google Drive|OneDrive|\bcd\s+["']?/|os\.chdir|setwd\()""")


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}


def notebook(cells, kernel):
    return {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": kernel, "language_info": {"name": kernel["language"]}},
            "cells": cells}


def leading_comment(text, lang):
    t = text.lstrip()
    if lang == "python" and t[:3] in ('"""', "'''"):
        end = t.find(t[:3], 3)
        doc = [x.strip() for x in t[3:end if end > 0 else None].splitlines() if x.strip()]
        return doc[0] if doc else ""
    out = []
    for line in text.lstrip().splitlines()[:15]:
        s = line.strip()
        if lang == "stata" and (s.startswith("*") or s.startswith("//")):
            out.append(s.lstrip("*/ ").strip())
        elif lang != "stata" and s.startswith("#") and not s.startswith("#!"):
            out.append(s.lstrip("# ").strip())
        elif s.startswith('"""') or s.startswith("'''"):
            continue
        elif s:
            break
    return " ".join(x for x in out if x and not re.fullmatch(r"[-=*#/ ]+", x))


def stata_block_comments(text):
    """Spans (start, end) of Stata /* ... */ comments, which may nest and span lines. Ignores /* inside
    "strings" (e.g. "data/*.dta"), after // and on lines starting with *."""
    spans, depth, start, i, n = [], 0, 0, 0, len(text)
    line_start = True
    while i < n:
        c, two = text[i], text[i:i + 2]
        if depth == 0:
            if line_start and text[i:].lstrip(" \t").startswith("*") and not text[i:].lstrip(" \t").startswith("*/"):
                i = text.find("\n", i)
                i = n if i < 0 else i  # skip * comment line
                continue
            line_start = False
            if c == "\n":
                line_start = True
            elif two == "//":
                j = text.find("\n", i)
                i = n if j < 0 else j
                continue
            elif c == '"':
                j = text.find('"', i + 1)
                nl = text.find("\n", i + 1)
                if j < 0 or (0 <= nl < j):  # unterminated on this line
                    i += 1
                    continue
                i = j + 1
                continue
            elif two == "/*":
                depth, start = 1, i
                i += 2
                continue
        else:
            if two == "/*":
                depth += 1
                i += 2
                continue
            if two == "*/":
                depth -= 1
                i += 2
                if depth == 0:
                    spans.append((start, i))
                continue
        i += 1
    if depth:
        spans.append((start, n))
    return spans


def python_strings(text):
    """Spans of multi-line Python strings (docstrings), so dividers inside them are ignored."""
    import io
    import tokenize
    spans, offs = [], [0]
    for ln in text.splitlines(keepends=True):
        offs.append(offs[-1] + len(ln))
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.STRING and tok.start[0] != tok.end[0]:
                spans.append((offs[tok.start[0] - 1] + tok.start[1], offs[tok.end[0] - 1] + tok.end[1]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return spans


def protected_spans(text, lang):
    return stata_block_comments(text) if lang == "stata" else python_strings(text) if lang == "python" else []


def split(text, lang):
    rx = DIVIDERS[lang]
    spans = protected_spans(text, lang)

    def inside(m):
        pos = m.start() + len(m.group()) - len(m.group().lstrip())
        for s, e in spans:
            if pos == s and m.end() >= e:
                return False  # the whole comment is a one-line divider, e.g. /* ---- */
            if s <= pos < e:
                return True
        return False
    marks = [m for m in rx.finditer(text) if not inside(m)]
    if not marks:
        return [("", text)]
    parts, prev, title = [], 0, ""
    for m in marks:
        body = text[prev:m.start()]
        if body.strip():
            parts.append((title, body))
        title = re.sub(r"^[\s#/*%=\-]+|[\s#/*%=\-]+$", "", m.group()).strip()
        prev = m.end()
    if text[prev:].strip():
        parts.append((title, text[prev:]))
    return parts


def convert(src: Path, lang: str, stata_mode: str, label: str):
    text = read_text_retry(src).replace("\r\n", "\n").replace("\r", "\n")
    kernel = KERNELS["python"] if lang in ("python",) or (lang == "stata" and stata_mode == "pystata") \
        else KERNELS["stata_kernel"] if lang == "stata" else KERNELS["r"]
    desc = leading_comment(text, lang) or f"Runs `{src.name}`."
    cells = [md(f"# {src.stem.replace('_', ' ')}\n\n{desc}\n\n"
                f"*Migrated from `{label or src.name}`. Paths are relative to this notebook's folder "
                f"(`progs/<Lang>/`), e.g. `../../data/...`.*")]
    if lang == "stata" and stata_mode == "pystata":
        cells.append(code("import stata_init"))
    pieces = [("", text)] if (lang == "stata" and re.search(r"^\s*#d(elimit)?\s*;", text, re.M)) else split(text, lang)
    cmt = re.compile(r"^\s*(\*|//|#(?!delimit)|/\*|\*/)") if lang == "stata" else re.compile(r"^\s*#")
    pending = ""
    for title, body in pieces:
        body = body.strip("\n")
        if not body.strip():
            if title:
                pending += f"## {title}\n"
            continue
        if all(cmt.match(ln) or not ln.strip() for ln in body.splitlines()):
            # comment-only block between dividers -> markdown for the next code cell
            txt = "\n".join(re.sub(r"^\s*(\*+|//+|#+|/\*|\*/)\s?", "", ln).rstrip(" */") for ln in body.splitlines())
            txt = txt.strip()
            pending += (f"## {title}\n" if title else "") + (f"## {txt}" if "\n" not in txt and len(txt) < 90 else txt) + "\n"
            continue
        if title or pending:
            cells.append(md(((f"## {title}\n" if title else "") + pending).strip()))
            pending = ""
        if lang == "stata" and stata_mode == "pystata":
            body = "%%stata\n" + body
        cells.append(code(body))
    nb = notebook(cells, kernel)
    warnings = [f"  line {i}: {ln.strip()[:120]}" for i, ln in enumerate(text.splitlines(), 1) if SUSPECT_PATH.search(ln)]
    return nb, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", choices=["python", "stata", "r"], required=True)
    ap.add_argument("--stata-mode", choices=["pystata", "stata_kernel"], default="pystata")
    ap.add_argument("--source-label", default="", help="original relative path, recorded in the header cell")
    ap.add_argument("source", type=Path)
    ap.add_argument("dest", type=Path)
    a = ap.parse_args()
    if not a.source.exists():
        sys.exit(f"source not found: {a.source}")
    if a.source.suffix.lower() == ".ipynb":
        sys.exit("already a notebook — copy it instead (and fix its kernelspec/paths)")
    if re.search(r"\s", a.dest.name):
        good = re.sub(r"\s+", "-", a.dest.name.strip())
        sys.exit(f"destination name has spaces: use '{good}' (package names never contain spaces)")
    nb, warns = convert(a.source, a.lang, a.stata_mode, a.source_label)
    assert_writable(a.dest, [a.source.resolve().parent])
    a.dest.parent.mkdir(parents=True, exist_ok=True)
    a.dest.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"✅ {a.source.name} → {a.dest} ({len(nb['cells'])} cells, kernel {nb['metadata']['kernelspec']['name']})")
    if warns:
        print(f"⚠️  {len(warns)} line(s) with absolute paths / cd / chdir — fix with audit_paths.py:")
        print("\n".join(warns[:15]))


if __name__ == "__main__":
    main()
