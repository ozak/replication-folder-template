# Figure and Table Naming Conventions

## Standard convention

Files are named by order of appearance in the paper, with a **hyphen** before panel letters:

| Type | Convention | Example |
|---|---|---|
| Main figure | `Figure-N.ext` | `Figure-1.pdf` |
| Main figure with panels | `Figure-N-a.ext`, `Figure-N-b.ext` | `Figure-2-a.jpg`, `Figure-2-b.jpg` |
| Main table | `Table-N.tex` | `Table-1.tex` |
| Multi-panel table | `Table-N-PanelA.tex`, `Table-N-PanelB.tex` | `Table-2-PanelA.tex` |

## Appendix naming

Appendix figures and tables use the **appendix section letter** as a prefix, followed by the figure/table number within that section:

| Type | Convention | Example |
|---|---|---|
| Appendix D figure | `Figure-D-N.ext` | `Figure-D-1.pdf` |
| Appendix D figure with panels | `Figure-D-N-a.ext` | `Figure-D-1-a.jpg` |
| Appendix D table | `Table-D-N.tex` | `Table-D-1.tex` |
| Appendix E figure | `Figure-E-N.ext` | `Figure-E-1.pdf` |
| Appendix E table | `Table-E-N.tex` | `Table-E-1.tex` |

If there is only a single appendix section (no named subsections), use `A` as the letter:
- `Figure-A-1.pdf`, `Table-A-1.tex`

The letter corresponds to the `\section{Appendix D}` or `\appendix` section label in the LaTeX source.

## "Overview + panels" pattern

Some figures have both a combined overview image and individual panel images:
- `Figure-1.jpg` — the combined overview
- `Figure-1-a.jpg`, `Figure-1-b.jpg` — individual panels

This occurs when the figure environment contains both a full `\includegraphics` and subfigure panels. Both the overview and the panels get names under the same figure number.

## How to determine numbering from LaTeX

Walk the `.tex` file linearly:
1. Each `\begin{figure}` or `\begin{figure*}` increments the figure counter
2. Multiple `\includegraphics` within one `\begin{figure}` → panels (a, b, c…)
3. Each `\begin{table}` increments the table counter
4. `\appendix` or a named `\section{Appendix X}` resets numbering to the section letter
5. A file referenced multiple times → keep the name from first occurrence

## Extension handling

Match the source file's extension. Don't convert formats.

Common: `.pdf` (vector), `.jpg` (raster color), `.png` (raster with transparency), `.eps` (legacy)

## Continuation files

Long tables split across files use a `-cont` suffix:
- `Table-D-6.tex`, `Table-D-6-cont.tex`, `Table-D-6-cont2.tex`

## Where files go

All final output files (both main paper AND appendix) go into:
- `replication-package/graphs/paper/` — all figures
- `replication-package/tables/paper/` — all tables

The `1-paper/graphs/paper/` and `2-appendix/graphs/paper/` directories contain **copies** of the relevant subset, needed for LaTeX compilation of each document separately.
