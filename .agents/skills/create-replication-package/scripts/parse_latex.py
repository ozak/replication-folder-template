#!/usr/bin/env python3
"""
Parse the final LaTeX source(s) of a paper and propose standardized names for every
figure and table, following the template's hyphenated convention:

    Figure-1            single figure
    Figure-1-a          panel (subfloat / several graphics in one float)
    Figure-1            + Figure-1-a, Figure-1-b   overview graphic in \\multicolumn plus panels
    Figure-B1-a1        grid of plain graphics: letter = column, number = row
    Figure-D1, Table-D1 appendix items: section letter fused with number (as LaTeX prints "Figure D1")
    Table-2-Panel-A     several \\input files inside one table float
    Table-D6-cont       \\ContinuedFloat continuation (then -cont2, -cont3, ...)

Usage:
    python parse_latex.py MAIN.tex [APPENDIX.tex ...] \
        --project-root <source-project-root> \
        --output rename_map.json --print

The first file is the main paper; later files are appendix documents. Within any file,
\\appendix (or \\begin{appendix}) starts appendix numbering; each *unstarred* \\section
after it advances the letter (A, B, C, ...). Starred sections (e.g. \\section*{Online
Appendix}) do not. Section files pulled in with \\input/\\include are expanded.

Output JSON: {"documents": [...], "entries": [...]} where each entry has
kind, name, location (paper|appendix), doc, origin, line, label, caption,
latex_path (as written), latex_new_path (to write in the new .tex), sources (files found
on disk, relative to --project-root), dest (paths inside replication-package/),
status (ok | missing | inline | unresolved | duplicate), hint (for inline tables).

Statuses to review with the user:
  missing     graphic/table file referenced but not found on disk
  inline      table body pasted into the .tex (no \\input). Use match_inline_tables.py
              or the `hint` (a path mentioned in nearby comments) to find the generating file.
  unresolved  top-level \\input that looks like a table but could not be opened
  duplicate   same file referenced twice; keeps the first name
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry, probe  # noqa: E402

GRAPHIC_EXTS = [".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".tif", ".tiff", ".gif"]
FIG_ENV = r"(?:figure|sidewaysfigure|wrapfigure)\*?"
TAB_ENV = r"(?:table|sidewaystable|longtable|wraptable)\*?"

RE_COMMENT = re.compile(r"(?<!\\)%[^\n]*")
RE_INPUT = re.compile(r"\\(input|include|subfile)\s*\{([^}]+)\}")
RE_GRAPHICSPATH = re.compile(r"\\graphicspath\s*\{((?:\{[^}]*\}\s*)+)\}")
RE_EVENTS = re.compile(
    r"(?P<appendix>\\appendix\b|\\begin\{appendix\})"
    r"|(?P<section>\\section(?P<star>\*?)\s*(?:\[[^\]]*\])?\s*\{)"
    r"|(?P<fbegin>\\begin\{" + FIG_ENV + r"\})"
    r"|(?P<fend>\\end\{" + FIG_ENV + r"\})"
    r"|(?P<tbegin>\\begin\{" + TAB_ENV + r"\})"
    r"|(?P<tend>\\end\{" + TAB_ENV + r"\})"
    r"|(?P<input>\\(?:input|include)\s*\{(?P<ipath>[^}]+)\})"
    r"|(?P<graphic>\\includegraphics\s*(?:\[[^\]]*\])?\s*\{(?P<gpath>[^}]+)\})"
)
RE_SUBPANEL = re.compile(r"\\subfloat|\\subfigure|\\begin\{subfigure\}|\\subcaptionbox")
RE_ADDTO = re.compile(r"\\addtocounter\{(?:figure|table)\}\{-1\}\s*$")
RE_MARK = re.compile(r"%%RPKG-ORIGIN (.+?)%%\n")


def blank_comments(text: str) -> str:
    """Replace comments by spaces so positions stay aligned with the raw text."""
    return RE_COMMENT.sub(lambda m: " " * len(m.group()), text)


def read(path: Path) -> str:
    try:
        return read_text_retry(path)
    except OSError as e:  # e.g. Dropbox online-only file ("Resource deadlock avoided")
        print(f"⚠️  Cannot read {path}: {e}. Make it available offline and re-run.", file=sys.stderr)
        return ""


def resolve_tex(base_dir: Path, p: str):
    p = p.strip()
    cand = base_dir / p
    for c in (cand, cand.with_name(cand.name + ".tex")):
        if c.is_file():
            return c
    return None


def float_depth_at(blank: str, pos: int) -> int:
    depth = 0
    for m in re.finditer(r"\\(begin|end)\{(?:" + FIG_ENV + "|" + TAB_ENV + r")\}", blank[:pos]):
        depth += 1 if m.group(1) == "begin" else -1
    return depth


def expand(path: Path, depth: int = 0) -> str:
    """Inline \\input'ed section files (not table bodies, not full-table files)."""
    raw = read(path)
    if depth > 6:
        return raw
    blank = blank_comments(raw)
    out, last = [], 0
    for m in RE_INPUT.finditer(blank):
        if float_depth_at(blank, m.start()) > 0:
            continue
        target = resolve_tex(path.parent, m.group(2))
        if target is None:
            continue
        tblank = blank_comments(read(target))
        is_table_file = re.search(r"\\begin\{" + TAB_ENV + r"\}", tblank) and not re.search(r"\\(sub)*section", tblank)
        is_structural = re.search(r"\\(sub)*section|\\begin\{" + FIG_ENV + r"\}|\\includegraphics|\\input|\\appendix", tblank)
        if is_table_file or not is_structural:
            continue
        out.append(raw[last:m.start()])
        resume = raw[:m.end()].count("\n") + 1
        out.append(f"\n%%RPKG-ORIGIN {target}|1%%\n" + expand(target, depth + 1) +
                   f"\n%%RPKG-ORIGIN {path}|{resume}%%\n")
        last = m.end()
    out.append(raw[last:])
    return "".join(out)


def balanced(text: str, start: int) -> str:
    """Return the content of the {...} group starting at text[start] == '{'."""
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif text[i] == "}" and text[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
        i += 1
    return text[start + 1:]


def label_caption(body: str):
    lab = re.search(r"\\label\{([^}]+)\}", body)
    cap = ""
    m = re.search(r"\\caption\s*(?:\[[^\]]*\])?\s*\{", body)
    if m:
        cap = re.sub(r"\\label\{[^}]*\}", "", balanced(body, m.end() - 1))
        cap = re.sub(r"\s+", " ", cap).strip()[:140]
    return (lab.group(1) if lab else ""), cap


class Parser:
    def __init__(self, project_root: Path, first_letter: str = "A"):
        self.root = project_root
        self.first_letter = first_letter
        self.entries = []
        self.seen = {}           # resolved source key -> name
        self.fig_n = 0           # main-text counters
        self.tab_n = 0

    # ---------- file resolution ----------
    def find_sources(self, base_dirs, latex_path, kind):
        p = latex_path.strip().strip('"')
        exts = GRAPHIC_EXTS if kind == "figure" else [".tex"]
        found = []
        for d in base_dirs:
            c = (d / p)
            if c.suffix.lower() in exts and c.is_file():
                found = [c]
                break
            stem = c.name[:-len(c.suffix)] if c.suffix.lower() in exts else c.name
            if c.parent.is_dir():
                hits = sorted(x for x in c.parent.glob(glob_escape(stem) + ".*") if x.suffix.lower() in exts)
                if hits:
                    found = hits
                    break
        return [os.path.relpath(f, self.root) for f in found]

    def add(self, **e):
        key = None
        if e.get("sources"):
            key = tuple(sorted(e["sources"]))
        elif e.get("latex_path"):
            key = (e["latex_path"],)
        if key and key in self.seen and e["status"] != "inline":
            e["status"] = "duplicate"
            e["name"], e["location"] = self.seen[key]
            e["note"] = f"same file as {e['name']}; keeps the first name"
        elif key:
            self.seen[key] = (e["name"], e["location"])
        loc = e["location"]
        folder = "graphs" if e["kind"] == "figure" else "tables"
        lp = e.get("latex_path", "")
        if e["kind"] == "figure":
            has_ext = Path(lp).suffix.lower() in GRAPHIC_EXTS
            exts = [Path(s).suffix for s in e.get("sources", [])] or ([Path(lp).suffix] if has_ext else [])
            e["dest"] = sorted({f"{folder}/{loc}/{e['name']}{x}" for x in exts})
            e["latex_new_path"] = f"{folder}/{loc}/{e['name']}" + (Path(lp).suffix if has_ext else "")
        else:
            e["dest"] = [f"{folder}/{loc}/{e['name']}.tex"]
            e["latex_new_path"] = f"{folder}/{loc}/{e['name']}" + (".tex" if lp.endswith(".tex") else "")
            if e.get("sources") and e["status"] in ("ok",):
                # Is the referenced file a complete (often hand-edited) table — with its own tabular
                # head/foot — or only body rows? Complete files get split: head/foot move into the
                # paper, the package generates only the body (rewrite_tex_paths.py does the move).
                ft = blank_comments(read(self.root / e["sources"][0]))
                if re.search(r"\\begin\{(?:tabular|tabularx|longtable)|\\toprule|\\bottomrule|\\caption", ft):
                    e["table_file"] = "full"
                    span = table_body_span(ft)
                    e["fingerprint"] = list(dict.fromkeys(re.findall(r"-?\d+\.\d+", ft[span[0]:span[1]] if span else ft)))[:400]
                    if not span:
                        e["note"] = (e.get("note", "") + "; complete table file without \\midrule/\\bottomrule — split head/body/foot by hand").strip("; ")
                else:
                    e["table_file"] = "body"
        self.entries.append(e)

    # ---------- main walk ----------
    def parse(self, tex: Path, role: str):
        text = expand(tex)
        blank = blank_comments(text)
        # \graphicspath dirs
        base_dirs = [tex.parent]
        for g in RE_GRAPHICSPATH.finditer(blank):
            for d in re.findall(r"\{([^}]*)\}", g.group(1)):
                base_dirs.append((tex.parent / d).resolve())
        marks = [(m.end(), m.group(1)) for m in RE_MARK.finditer(text)]

        def origin_line(pos):
            org, start, line0 = str(tex), 0, 1
            for mend, mpath in marks:
                if mend <= pos:
                    org, line0 = mpath.rsplit("|", 1)
                    start, line0 = mend, int(line0)
            return os.path.relpath(org, self.root), line0 + text[start:pos].count("\n")

        in_app = role == "appendix"
        letter_idx = -1          # number of unstarred sections seen since \appendix
        app_counts = {}          # letter -> (fig, tab)
        cur = None               # current float {"kind","start","graphics","inputs"}
        last_table = None        # for \ContinuedFloat

        def number(kind, cont):
            nonlocal last_table
            if in_app:
                letter = chr(ord(self.first_letter) + max(letter_idx, 0))
                f, t = app_counts.get(letter, (0, 0))
                if not cont:
                    f, t = (f + 1, t) if kind == "figure" else (f, t + 1)
                app_counts[letter] = (f, t)
                return f"{letter}{f if kind == 'figure' else t}", "appendix"
            if not cont:
                if kind == "figure":
                    self.fig_n += 1
                else:
                    self.tab_n += 1
            return str(self.fig_n if kind == "figure" else self.tab_n), "paper"

        for m in RE_EVENTS.finditer(blank):
            g = m.groupdict()
            if g["appendix"]:
                in_app, letter_idx = True, -1
            elif g["section"] is not None and g["section"]:
                if in_app and not g["star"]:
                    letter_idx += 1
            elif g["fbegin"] or g["tbegin"]:
                if cur is None:
                    cur = {"kind": "figure" if g["fbegin"] else "table", "start": m.start(),
                           "graphics": [], "inputs": []}
            elif g["fend"] or g["tend"]:
                if cur is not None:
                    self.close_float(cur, text, blank, m.end(), base_dirs, number, origin_line)
                    cur = None
            elif g["graphic"]:
                if cur is not None:
                    cur["graphics"].append((m.start(), g["gpath"]))
                else:
                    o, ln = origin_line(m.start())
                    print(f"note: graphic outside a float ignored: {g['gpath']} ({o}:{ln})", file=sys.stderr)
            elif g["input"]:
                if cur is not None:
                    cur["inputs"].append((m.start(), g["ipath"]))
                else:
                    self.top_level_input(g["ipath"], m.start(), tex, base_dirs, number, origin_line)

    def top_level_input(self, ipath, pos, tex, base_dirs, number, origin_line):
        target = resolve_tex(tex.parent, ipath)
        o, ln = origin_line(pos)
        if target is not None:
            tb = blank_comments(read(target))
            kind = "table" if re.search(r"\\begin\{" + TAB_ENV + r"\}", tb) else (
                "figure" if re.search(r"\\begin\{" + FIG_ENV + r"\}", tb) else None)
            if kind is None:
                return
            cont = "\\ContinuedFloat" in tb
            num, loc = number(kind, cont)
            base = ("Figure-" if kind == "figure" else "Table-") + num
            name = self.cont_name(base) if cont else base
            lab, cap = label_caption(tb)
            self.add(kind=kind, name=name, location=loc, doc=str(tex), origin=o, line=ln, label=lab,
                     caption=cap, latex_path=ipath, sources=[os.path.relpath(target, self.root)],
                     status="ok", note="top-level \\input of a file containing the full float")
        elif re.search(r"tab", Path(ipath).name, re.I):
            num, loc = number("table", False)
            self.add(kind="table", name=f"Table-{num}", location=loc, doc=str(tex), origin=o, line=ln,
                     label="", caption="", latex_path=ipath, sources=[], status="unresolved",
                     note="top-level \\input not found; assumed to be a table — verify numbering")

    def cont_name(self, base):
        prior = [e["name"] for e in self.entries if e["name"] == base or e["name"].startswith(base + "-cont")]
        k = len([p for p in prior if "-cont" in p])
        return f"{base}-cont" + (str(k + 1) if k else "")

    def close_float(self, cur, text, blank, end, base_dirs, number, origin_line):
        body_b = blank[cur["start"]:end]
        body_raw = text[cur["start"]:end]
        cont = "\\ContinuedFloat" in body_b or bool(RE_ADDTO.search(blank[max(0, cur["start"] - 300):cur["start"]]))
        lab, cap = label_caption(body_b)
        o, ln = origin_line(cur["start"])
        common = dict(doc=None, origin=o, line=ln, label=lab, caption=cap)
        items_g, items_i = cur["graphics"], cur["inputs"]
        kind = cur["kind"]
        if not items_g and not items_i:
            if kind == "table":
                num, loc = number("table", cont)
                base = f"Table-{num}"
                name = self.cont_name(base) if cont else base
                hints = re.findall(r"%[^\n]*?([\w./\\ -]+\.(?:tex|txt|csv))", body_raw)
                fp = list(dict.fromkeys(re.findall(r"-?\d+\.\d+", body_b)))[:400]
                body = table_body_span(body_b)
                extra = {}
                if body:
                    a, b = body
                    o1, l1 = origin_line(cur["start"] + a)
                    o2, l2 = origin_line(cur["start"] + b)
                    if o1 == o2 == o:
                        extra = {"body_lines": [l1, l2 - 1], "body_text": body_raw[a:b].strip("\n")}
                self.add(kind="table", name=name, location=loc, latex_path="", sources=[],
                         status="inline", hint=[h.strip() for h in hints], fingerprint=fp, **extra, **common)
            return
        num, loc = number(kind, cont)
        prefix = "Figure-" if kind == "figure" else "Table-"
        base = prefix + num
        offset = 0
        if cont and (items_i or kind == "table"):
            base = self.cont_name(base)
        elif cont:  # continued figure: same number, panel letters continue (Figure-I4-f, -g, ...)
            offset = len([e for e in self.entries if e["name"].startswith(base + "-")])
        # tables built from \input files (panels)
        if items_i and not items_g:
            for i, (pos, p) in enumerate(items_i):
                name = base if len(items_i) == 1 else f"{base}-Panel-{chr(65 + i)}"
                srcs = self.find_sources(base_dirs, p, "table")
                self.add(kind=kind if kind == "table" else "figure", name=name, location=loc,
                         latex_path=p, sources=srcs, status="ok" if srcs else "missing", **common)
            return
        # graphics (figures, or image tables)
        names = self.panel_names(base, items_g, body_b, cur["start"], offset)
        for (pos, p), name in zip(items_g, names):
            srcs = self.find_sources(base_dirs, p, "figure")
            self.add(kind="figure" if kind == "figure" else "table-image", name=name, location=loc,
                     latex_path=p, sources=srcs, status="ok" if srcs else "missing", **common)
        for i, (pos, p) in enumerate(items_i):
            srcs = self.find_sources(base_dirs, p, "table")
            self.add(kind="table", name=f"{base}-input-{i + 1}", location=loc, latex_path=p, sources=srcs,
                     status="ok" if srcs else "missing", note="\\input inside figure float — check", **common)

    def panel_names(self, base, graphics, body, start, offset=0):
        """Name the graphics of one float. offset>0 continues panel letters (\\ContinuedFloat)."""
        n = len(graphics)
        if n == 1 and offset == 0:
            return [base]
        rel = [pos - start for pos, _ in graphics]
        # overview graphic: inside \multicolumn{..}{..}{ ... \includegraphics } with no & or \\ in between
        overview = set()
        for i, r in enumerate(rel):
            mc = body.rfind("\\multicolumn", 0, r)
            if mc != -1 and not re.search(r"(?<!\\)&|\\\\", body[mc:r]):
                overview.add(i)
        if len(overview) != 1 or n == 1:
            overview = set()
        panels = [i for i in range(n) if i not in overview]
        names = [None] * n
        for i in overview:
            names[i] = base
        sub_starts = [m.start() for m in RE_SUBPANEL.finditer(body)]
        if sub_starts:
            groups = {}
            for i in panels:
                k = sum(1 for s0 in sub_starts if s0 < rel[i])
                groups.setdefault(k, []).append(i)
            if any(len(v) >= 2 for v in groups.values()):
                # each subfigure holds a row of graphics: letter = position, number = subfigure index
                for rank, k in enumerate(sorted(groups)):
                    for col, i in enumerate(groups[k]):
                        names[i] = f"{base}-{chr(97 + col)}{rank + 1}"
                return names
            for k, i in enumerate(panels):
                names[i] = f"{base}-{chr(97 + offset + k)}"
            return names
        # grid detection inside a tabular: rows split by \\, columns by unescaped &
        coords = {}
        for i in panels:
            r = rel[i]
            tb = max(body.rfind("\\begin{tabular", 0, r), 0)
            seg = body[tb:r]
            row = len(re.findall(r"\\\\", seg))
            last_break = seg.rfind("\\\\")
            col = len(re.findall(r"(?<!\\)&", seg[last_break + 2 if last_break >= 0 else 0:]))
            coords[i] = (tb, row, col)
        rows = {}
        for i, key in coords.items():
            rows.setdefault(key[:2], []).append(i)
        if len([r for r, ids in rows.items() if len(ids) >= 2]) >= 2:
            row_rank = {r: k + 1 for k, r in enumerate(sorted(rows))}
            for i, (tb, row, col) in coords.items():
                names[i] = f"{base}-{chr(97 + col)}{row_rank[(tb, row)]}"
            return names
        for k, i in enumerate(panels):
            names[i] = f"{base}-{chr(97 + offset + k)}"
        return names


def table_body_span(body):
    """(start, end) offsets of the rows between the header rule and \\bottomrule of the first
    tabular in a float: the part the code generates. Head (caption, column headers) and foot
    (\\bottomrule, notes) stay in the paper. Returns None if no booktabs/hline rules are found."""
    t = re.search(r"\\begin\{(?:tabular|tabularx|tabular\*|longtable|threeparttable)\}", body)
    s0 = t.end() if t else 0
    end_tab = body.find("\\end{tabular", s0)
    end_tab = end_tab if end_tab != -1 else len(body)
    m = re.search(r"\\midrule[^\n]*\n", body[s0:end_tab])
    if m:
        a = s0 + m.end()
        b = body.find("\\bottomrule", a, end_tab)
        if b != -1:
            b = body.rfind("\n", a, b) + 1 or b
            return (a, b) if b > a else None
    hl = [x for x in re.finditer(r"\\hline[^\n]*\n", body[s0:end_tab])]
    if len(hl) >= 3:
        a = s0 + hl[1].end()
        b = s0 + hl[-1].start()
        b = body.rfind("\n", a, b) + 1 or b
        return (a, b) if b > a else None
    return None


def glob_escape(s: str) -> str:
    return re.sub(r"([*?\[\]])", r"[\1]", s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tex", nargs="+", type=Path, help="main .tex first, then appendix .tex file(s)")
    ap.add_argument("--project-root", type=Path, default=None,
                    help="source project root; sources are reported relative to it (default: parent of main .tex)")
    ap.add_argument("--appendix-first-letter", default="A")
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()

    root = (args.project_root or args.tex[0].resolve().parent).resolve()
    P = Parser(root, args.appendix_first_letter)
    docs = []
    for i, t in enumerate(args.tex):
        role = "main" if i == 0 else "appendix"
        docs.append({"tex": str(t), "role": role})
        P.parse(t.resolve(), role)
        for e in P.entries:
            if e.get("doc") is None:
                e["doc"] = str(t)
    for e in P.entries:
        e["doc"] = os.path.relpath(Path(e["doc"]).resolve(), root)
        e.setdefault("hint", [])
        e.setdefault("note", "")

    out = {"project_root": str(root), "style": "hyphen", "documents": docs, "entries": P.entries}
    if args.output:
        assert_writable(args.output, [root])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.print or not args.output:
        w = max([len(e["name"]) for e in P.entries] + [10])
        print(f"{'Name'.ljust(w)}  {'Status'.ljust(10)} {'Origin:line'.ljust(28)} Source(s) / hint")
        print("-" * 110)
        for e in P.entries:
            src = ", ".join(e["sources"]) or ("hint: " + "; ".join(e["hint"]) if e["hint"] else e["latex_path"])
            print(f"{e['name'].ljust(w)}  {e['status'].ljust(10)} {(e['origin'] + ':' + str(e['line'])).ljust(28)} {src}")
        counts = {}
        for e in P.entries:
            counts[e["status"]] = counts.get(e["status"], 0) + 1
        print(f"\n{len(P.entries)} entries: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if args.output:
        print(f"✅ Rename map written to {args.output}")


if __name__ == "__main__":
    main()
