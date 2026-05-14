#!/usr/bin/env python3
"""
Convert Python, Stata, or R scripts to Jupyter notebooks.

Usage:
    python scripts/convert_to_notebook.py --lang python source.py dest.ipynb
    python scripts/convert_to_notebook.py --lang stata source.do dest.ipynb
    python scripts/convert_to_notebook.py --lang r source.R dest.ipynb

The conversion is structural: code is split into cells at natural section boundaries
(comment-based dividers like `# ---`, `// ---`). Logic is preserved, not rewritten.
"""
import argparse
import json
import re
import sys
from pathlib import Path


KERNELS = {
    "python": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "stata":  {"name": "stata",   "display_name": "Stata",    "language": "stata"},
    "r":      {"name": "ir",      "display_name": "R",        "language": "R"},
}


def make_notebook(cells, kernel_info):
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "name": kernel_info["name"],
                "display_name": kernel_info["display_name"],
                "language": kernel_info["language"],
            },
            "language_info": {"name": kernel_info["language"]},
        },
        "cells": cells,
    }


def markdown_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code_cell(source):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": source}


def extract_inline_description(body: str, comment_char: str) -> str:
    """
    Pull consecutive comment lines from the top of a code block as a description.
    Returns plain text (comment chars stripped), empty string if none found.
    """
    lines = body.lstrip("\n").splitlines()
    desc_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(comment_char):
            desc_lines.append(stripped.lstrip(comment_char).strip())
        elif stripped == "":
            if desc_lines:
                break  # stop at blank line after comments
        else:
            break
    return " ".join(desc_lines).strip()


def split_sections(text, comment_char):
    """Split code into sections at lines that look like section dividers."""
    # Match lines like `# ---`, `// ===`, `// *** My Section ***`
    divider = re.compile(
        r"^" + re.escape(comment_char) + r"[-=*]{3,}.*$",
        re.MULTILINE,
    )
    positions = [(m.start(), m.end(), m.group()) for m in divider.finditer(text)]
    if not positions:
        return [("", text)]

    sections = []
    prev_end = 0
    for start, end, header in positions:
        body = text[prev_end:start]
        if body.strip() or sections:
            sections.append(("", body))
        sections.append((header, ""))
        prev_end = end + 1  # skip the newline
    sections.append(("", text[prev_end:]))
    # Merge: each header immediately followed by the next body
    merged = []
    i = 0
    while i < len(sections):
        header, body = sections[i]
        if header and i + 1 < len(sections):
            merged.append((header, sections[i + 1][1]))
            i += 2
        else:
            merged.append((header, body))
            i += 1
    return merged


def infer_file_purpose(text: str, lang: str, stem: str) -> str:
    """
    Produce a one-sentence description of what the file does, based on its name
    and leading comment block.
    """
    comment_char = {"python": "#", "stata": "//", "r": "#"}[lang]
    lines = text.lstrip().splitlines()
    leading = []
    for line in lines[:10]:
        s = line.strip()
        if s.startswith(comment_char):
            leading.append(s.lstrip(comment_char).strip())
        elif s:
            break
    if leading:
        return " ".join(leading)
    name = stem.replace("_", " ").replace("-", " ")
    return f"Runs the {name} analysis."


def to_notebook(source_path: Path, lang: str) -> dict:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    kernel = KERNELS[lang]
    purpose = infer_file_purpose(text, lang, source_path.stem)

    header_cell = markdown_cell(
        f"# {source_path.stem}\n\n"
        f"{purpose}\n\n"
        f"*Converted from `{source_path.name}`. "
        f"Verify that this notebook executes without errors before including in the replication package.*"
    )

    # For Python, try jupytext first (preserves richer structure if available)
    if lang == "python":
        try:
            import jupytext
            nb = jupytext.read(source_path)
            nb_json = json.loads(jupytext.writes(nb, fmt="notebook"))
            # Prepend the header cell if not already there
            if nb_json["cells"] and nb_json["cells"][0].get("cell_type") != "markdown":
                nb_json["cells"].insert(0, header_cell)
            return nb_json
        except (ImportError, Exception):
            pass

    comment_chars = {"python": "#", "stata": "//", "r": "#"}
    cc = comment_chars[lang]
    sections = split_sections(text, cc)

    cells = [header_cell]
    if len(sections) <= 1:
        cells.append(code_cell(text))
    else:
        for header, body in sections:
            if header:
                # Strip comment chars and divider characters to get a clean title
                title = re.sub(r"^[/#\-=*\s]+|[/#\-=*\s]+$", "", header).strip()
                desc = extract_inline_description(body, cc)
                md = f"## {title}" if title else "## (section)"
                if desc:
                    md += f"\n\n{desc}"
                cells.append(markdown_cell(md))
            if body.strip():
                cells.append(code_cell(body))

    return make_notebook(cells, kernel)


def main():
    parser = argparse.ArgumentParser(description="Convert scripts to Jupyter notebooks")
    parser.add_argument("--lang", choices=["python", "stata", "r"], required=True,
                        help="Target kernel language")
    parser.add_argument("source", type=Path, help="Source script file")
    parser.add_argument("dest", type=Path, help="Destination .ipynb file")
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Error: source file not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    nb = to_notebook(args.source, args.lang)
    args.dest.parent.mkdir(parents=True, exist_ok=True)
    args.dest.write_text(json.dumps(nb, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Converted {args.source} → {args.dest}")


if __name__ == "__main__":
    main()
