#!/usr/bin/env python3
"""
Parse LaTeX files to extract figure and table references and propose standardized names.

Usage:
    python scripts/parse_latex.py main.tex [appendix.tex] --output rename_map.json --print

The main file is parsed first. Files passed after the first are treated as additional
appendix files. Within a single file, the \\appendix command marks where appendix content
starts; subsequent \\section{} calls each increment the appendix letter (A, B, C, D...).

Outputs a JSON file mapping current filenames to proposed standardized names.
"""
import argparse
import json
import re
import sys
from pathlib import Path


INCLUDEGRAPHICS = re.compile(r"\\includegraphics(?:\[.*?\])?\{([^}]+)\}", re.DOTALL)
INPUT_TEX   = re.compile(r"\\input\{([^}]+)\}")
FIGURE_BEGIN = re.compile(r"\\begin\{figure\*?\}")
FIGURE_END   = re.compile(r"\\end\{figure\*?\}")
TABLE_BEGIN  = re.compile(r"\\begin\{table\*?\}")
TABLE_END    = re.compile(r"\\end\{table\*?\}")
APPENDIX_CMD = re.compile(r"\\appendix\b|\\begin\{appendix\}")
SECTION_CMD  = re.compile(r"\\section\*?\{")
COMMENT_PAT  = re.compile(r"%.*$", re.MULTILINE)


def strip_comments(text: str) -> str:
    return COMMENT_PAT.sub("", text)


def clean_path(path_str: str) -> str:
    p = path_str.strip()
    return re.sub(r"^\.\.?/", "", p)


def get_appendix_letter(pos: int, appendix_pos: int, section_positions: list[int]) -> str:
    """
    Return the appendix letter (A, B, C, ...) for a figure/table at `pos`,
    based on how many \\section{} commands appear between \\appendix and `pos`.
    The first section after \\appendix = A, second = B, etc.
    """
    if pos < appendix_pos:
        return ""  # not in appendix
    secs_before = sum(1 for sp in section_positions if appendix_pos <= sp < pos)
    letter = chr(ord("A") + max(0, secs_before - 1)) if secs_before > 0 else "A"
    return letter


def parse_file(tex_path: Path, is_appendix: bool = False) -> list[dict]:
    """
    Return an ordered list of references found in the LaTeX file.
    Each entry: {type, current_path, is_appendix, app_letter, pos}
    """
    raw = tex_path.read_text(encoding="utf-8", errors="replace")
    text = strip_comments(raw)

    # Locate \\appendix command (or treat whole file as appendix if is_appendix=True)
    app_match = APPENDIX_CMD.search(text)
    appendix_pos = app_match.start() if app_match else (0 if is_appendix else len(text))

    # Collect all \section{} positions that come AFTER \appendix
    section_positions = [m.start() for m in SECTION_CMD.finditer(text)
                         if m.start() >= appendix_pos]

    refs = []

    # --- Figures via \includegraphics ---
    for m in INCLUDEGRAPHICS.finditer(text):
        pos = m.start()
        path = clean_path(m.group(1))
        in_app = is_appendix or pos >= appendix_pos
        app_letter = get_appendix_letter(pos, appendix_pos, section_positions) if in_app else ""
        refs.append({
            "type": "figure",
            "current_path": path,
            "is_appendix": in_app,
            "app_letter": app_letter,
            "pos": pos,
        })

    # --- Tables via \input inside \begin{table}...\end{table} ---
    events = []
    for m in TABLE_BEGIN.finditer(text):
        events.append(("table_begin", m.start()))
    for m in TABLE_END.finditer(text):
        events.append(("table_end", m.start()))
    for m in INPUT_TEX.finditer(text):
        path = clean_path(m.group(1))
        if not path.endswith(".tex"):
            path = path + ".tex"
        events.append(("input", m.start(), path))

    events.sort(key=lambda x: x[1])

    depth = 0
    current_inputs = []
    for ev in events:
        if ev[0] == "table_begin":
            depth += 1
            if depth == 1:
                current_inputs = []
        elif ev[0] == "table_end":
            if depth == 1 and current_inputs:
                pos0 = current_inputs[0][0]
                in_app = is_appendix or pos0 >= appendix_pos
                app_letter = get_appendix_letter(pos0, appendix_pos, section_positions) if in_app else ""
                for inp_pos, inp_path in current_inputs:
                    refs.append({
                        "type": "table",
                        "current_path": inp_path,
                        "is_appendix": in_app,
                        "app_letter": app_letter,
                        "pos": inp_pos,
                    })
            depth = max(0, depth - 1)
        elif ev[0] == "input" and depth >= 1:
            current_inputs.append((ev[1], ev[2]))

    refs.sort(key=lambda x: x["pos"])
    return refs


def detect_panels(refs: list[dict], tex_text: str) -> list[dict]:
    """
    Detect panels within the same figure environment.
    Sets env_id and panel ('a','b',...) on each ref.
    Single-image environments get env_id but panel=None.
    """
    fig_envs = []
    for bm in FIGURE_BEGIN.finditer(tex_text):
        em = FIGURE_END.search(tex_text, bm.end())
        if em:
            fig_envs.append((bm.start(), em.end()))

    for env_id, (start, end) in enumerate(fig_envs):
        in_env = [r for r in refs if r["type"] == "figure" and start <= r["pos"] < end]
        if len(in_env) > 1:
            for j, r in enumerate(in_env):
                r["env_id"] = env_id
                r["panel"] = chr(ord("a") + j)
        elif len(in_env) == 1:
            in_env[0]["env_id"] = env_id
            in_env[0]["panel"] = None

    return refs


def build_rename_map(all_refs: list[dict]) -> dict[str, str]:
    """
    Assign standardized names. Panel-aware: figures sharing the same env_id
    get the same base counter. Appendix figures/tables use their section letter.
    """
    # Counters per appendix letter and for main content
    fig_main = 0
    tab_main = 0
    fig_app: dict[str, int] = {}   # letter → count
    tab_app: dict[str, int] = {}

    assigned: dict[str, str] = {}
    seen_env: dict[int, str] = {}

    for ref in all_refs:
        path = ref["current_path"]
        if path in assigned:
            continue

        env_id = ref.get("env_id")
        panel  = ref.get("panel")
        letter = ref.get("app_letter", "")

        if ref["type"] == "figure":
            if env_id is not None and env_id in seen_env:
                base = seen_env[env_id]
            else:
                if ref["is_appendix"]:
                    fig_app[letter] = fig_app.get(letter, 0) + 1
                    base = f"Figure-{letter}-{fig_app[letter]}"
                else:
                    fig_main += 1
                    base = f"Figure-{fig_main}"
                if env_id is not None:
                    seen_env[env_id] = base

            assigned[path] = base + ("-" + panel if panel else "")

        else:  # table
            if ref["is_appendix"]:
                tab_app[letter] = tab_app.get(letter, 0) + 1
                assigned[path] = f"Table-{letter}-{tab_app[letter]}"
            else:
                tab_main += 1
                assigned[path] = f"Table-{tab_main}"

    return assigned


def main():
    parser = argparse.ArgumentParser(
        description="Parse LaTeX to propose standardized figure/table names"
    )
    parser.add_argument("tex_files", nargs="+", type=Path,
                        help="LaTeX files (main paper first, then appendix if separate)")
    parser.add_argument("--output", type=Path, default=Path("rename_map.json"),
                        help="Output JSON mapping (default: rename_map.json)")
    parser.add_argument("--print", dest="print_map", action="store_true",
                        help="Print proposed mapping as a table")
    args = parser.parse_args()

    all_refs = []
    for i, tex_file in enumerate(args.tex_files):
        if not tex_file.exists():
            print(f"Warning: file not found: {tex_file}", file=sys.stderr)
            continue
        text = strip_comments(tex_file.read_text(encoding="utf-8", errors="replace"))
        refs = parse_file(tex_file, is_appendix=(i > 0))
        refs = detect_panels(refs, text)
        all_refs.extend(refs)

    rename_map = build_rename_map(all_refs)

    if args.print_map:
        print(f"\n{'Current path':<55} → {'Proposed name'}")
        print("-" * 80)
        for current, proposed in rename_map.items():
            print(f"{current:<55} → {proposed}")
        print(f"\n{len(rename_map)} entries total.\n")

    args.output.write_text(json.dumps(rename_map, indent=2), encoding="utf-8")
    print(f"✅ Rename map written to {args.output}")


if __name__ == "__main__":
    main()
