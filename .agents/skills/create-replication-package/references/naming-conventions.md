# Figure and Table Naming Conventions

Final files are named by **what LaTeX prints**, hyphen-separated. `parse_latex.py` applies these
rules; this page explains them so you can review its proposals with the user.

## Main text

| What LaTeX shows | File name | Notes |
|---|---|---|
| Figure 3 | `Figure-3.pdf` | one graphic in the float |
| Figure 6(a), 6(b) | `Figure-6-a.pdf`, `Figure-6-b.pdf` | several graphics, or `\subfloat`/`\subfigure` panels |
| Figure 1 with a full-width map plus two panels | `Figure-1.jpg`, `Figure-1-a.jpg`, `Figure-1-b.jpg` | the graphic inside `\multicolumn` is the *overview* and keeps the bare name |
| Table 1 | `Table-1.tex` | one `\input` (or one top-level `\input` of a file holding the whole `table` float) |
| Table 2, Panels A–C | `Table-2-Panel-A.tex`, `Table-2-Panel-B.tex`, `Table-2-Panel-C.tex` | several `\input`s inside one table float |

## Appendix

The appendix **section letter is fused with the number**, exactly like LaTeX prints it
(`\counterwithin{figure}{section}` → "Figure D1"):

| What LaTeX shows | File name |
|---|---|
| Figure C1(a) … C1(d) | `Figure-C1-a.pdf` … `Figure-C1-d.pdf` |
| Table D1 | `Table-D1.tex` |
| Table E2, Panel A | `Table-E2-Panel-A.tex` |
| Table D6 continued, continued again | `Table-D6-cont.tex`, `Table-D6-cont2.tex` |

Letters: after `\appendix`, each **unstarred** `\section` advances the letter (A, B, C, …).
Starred sections (`\section*{Online Appendix}`) do not. Sections without floats still consume a
letter (CountryStability: A = Endogenous Identity Choice, B = Data Sources, C = Language and
Religion → first figure is `Figure-C1-a`). If the appendix document restarts or offsets the
letters, pass `--appendix-first-letter`.

## Grids of panels

A figure laid out as a grid of plain graphics (rows × columns in a `tabular`, or one
`\subfigure` per row each holding a row of graphics) is named **column letter + row number**:

```
Figure-B1-a1  Figure-B1-b1  Figure-B1-c1
Figure-B1-a2  Figure-B1-b2  Figure-B1-c2
Figure-B1-a3  Figure-B1-b3  Figure-B1-c3
```

(OriginLanguages, Appendix B: 3 linguistic traits × 3 specifications.)

## Continued floats

* Tables continued with `\ContinuedFloat` or `\addtocounter{table}{-1}` → `-cont`, `-cont2`, …
* Figures continued the same way keep their number and **continue the panel letters**:
  `Figure-I4-a … Figure-I4-e` on the first page, `Figure-I4-f … Figure-I4-j` on the continuation;
  `Figure-F1-a`, `Figure-F1-b`, then `Figure-F1-c` alone on the next page.

## Extensions and formats

* Keep the source extension; never convert formats.
* If the `.tex` omits the extension and several formats exist (`Figure-2.pdf` and `Figure-2.jpg`),
  copy all of them — LaTeX picks one, journals sometimes ask for the other.
* If a file is referenced twice, the first name wins (`duplicate` status).
* No spaces in any name in the package: whitespace becomes `-` (runs collapse to one), for
  folders, code, data and outputs alike (`GDP data.csv` → `GDP-data.csv`, `World Bank/` →
  `World-Bank/`). Log each rename and update every reference in code, `.tex` and `index.ipynb`.

## Where the files go

| Folder | Contents |
|---|---|
| `replication-package/graphs/paper/`, `tables/paper/` | numbered (main-text) figures and tables |
| `replication-package/graphs/appendix/`, `tables/appendix/` | lettered (appendix) figures and tables |
| `1-paper/graphs/`, `1-paper/tables/` | flat copies of exactly what the main `.tex` uses |
| `2-appendix/graphs/`, `2-appendix/tables/` | flat copies of exactly what the appendix `.tex` uses |

The `.tex` files reference the flat folder next to them (`./graphs/Figure-1-a`, `./tables/Table-D3`);
names are unique across paper and appendix, so no subfolder is needed. `Copy-Final.ipynb` reads both
`.tex` files, finds each referenced file in `replication-package/graphs|tables/(paper|appendix)/` and
copies it next to the document that uses it — appendix items used in the main text (e.g. an EJ
"Appendix A" inside the paper) are handled automatically.

## What a table file contains

For tables whose body was pasted in the paper, `Table-N.tex` holds **only the body rows** (between
the header `\midrule` and `\bottomrule`); caption, column headers and notes stay in the paper's
`.tex`, which `\input`s the file inside its `tabular`. Multi-panel tables get one body file per panel
(`Table-N-Panel-A.tex`), with panel header rows kept in the `.tex`. The same applies when the paper
`\input`/`\include`d a complete (often hand-edited) table file: its head and foot are moved into the
paper and `Table-N.tex` becomes body-only.

## Things to confirm with the user

* Panel order when graphics are not in reading order in the source.
* Images that are not analysis outputs (photographs, scanned maps): they still get standard
  names (`Figure-H2.png`), are copied from `raw-data/` or `graphs/`, and their source/licence goes
  in the README.
* Inconsistent names in an earlier package (OriginLanguages used `Figure-H3` + `Figure-H3b`;
  the convention gives `Figure-H3-a`, `Figure-H3-b`).
