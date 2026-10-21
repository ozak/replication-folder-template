#!/usr/bin/env python3
"""
Paper and author information for ONE replication package, stored inside it:
    <target>/replication-info.json
(never in the user's home folder — papers have different co-authors, and the package must carry
its own metadata). The README, index.ipynb and paper templates are filled from this file.

Subcommands
    extract  --tex FINAL.tex [--tex APPENDIX.tex] --out draft.json
             Draft title, authors, affiliations, emails, ORCIDs and acknowledgements from the
             paper's LaTeX (\\title, \\author, \\thanks, \\affil, \\and, emails, ORCID iDs).
             Every value records where it came from ("tex:<file>").
    set      --file info.json --json '{"authors":[...], "title":"..."}'   (deep-merge; authors
             are matched by name) or --author "Name" --field key=value ... [source=<url>]
    show     --file info.json         table of authors/fields, what is missing, confirmation state
    confirm  --file info.json         mark the author list as confirmed by the user
    tokens   --file info.json         print the template tokens (JSON) — used by apply_defaults.py

Workflow (SKILL.md, Phase 1 / new project):
  1. extract from the final .tex (conversion) — or, for a new project, ask the user for the title
     and the co-authors' names;
  2. complete missing fields (affiliation, website, ORCID, email) with web searches, recording
     each source URL in the author's "sources";
  3. show the table to the user and ask them to confirm the authors and details; then `confirm`.
apply_defaults.py refuses to fill author tokens from an unconfirmed file.

Author fields: name, first_name, last_name, email, website, orcid, affiliation,
affiliation_short, thanks (acknowledgement text), corresponding (bool), sources (list).
Paper fields: title, subtitle, manuscript_id, journal, year, doi, short_title.
Compute fields (machine used to run the package): laptop_specs, laptop_memory, cluster_specs,
compute_hours. Logos: list of {url, width, link}.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable, read_text_retry  # noqa: E402

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
ORCID = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
URL = re.compile(r"https?://[^\s}{\\,]+")
REQUIRED_AUTHOR = ["name", "affiliation"]
RECOMMENDED_AUTHOR = ["email", "website", "orcid"]


# ---------------------------------------------------------------- LaTeX helpers
def strip_comments(t):
    return re.sub(r"(?<!\\)%[^\n]*", "", t)


def group(text, start):
    """content of the {...} group starting at text[start]=='{'"""
    d, i = 0, start
    while i < len(text):
        c = text[i]
        if c == "{" and text[i - 1] != "\\":
            d += 1
        elif c == "}" and text[i - 1] != "\\":
            d -= 1
            if d == 0:
                return text[start + 1:i], i + 1
        i += 1
    return text[start + 1:], len(text)


def commands(text, name):
    """all arguments of \\name[opt]{arg}"""
    out = []
    for m in re.finditer(r"\\" + name + r"\*?\s*(\[[^\]]*\])?\s*\{", text):
        arg, end = group(text, m.end() - 1)
        out.append((m.group(1) or "", arg))
    return out


def detex(s):
    s = re.sub(r"\\(?:href)\{[^}]*\}\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\(?:url)\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\(?:textit|textbf|emph|textsc|text|mbox|small|footnotesize|large|Large|normalsize)\s*\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\(?:vspace|hspace)\*?\{[^}]*\}", " ", s)
    s = re.sub(r"\\\\(\[[^\]]*\])?", " ", s)
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
    s = s.replace("~", " ").replace("{", "").replace("}", "").replace("\\&", "&")
    return re.sub(r"\s+", " ", s).strip(" ,;.")


NAME_RX = re.compile(r"^[A-ZÀ-Þ][\w'’.-]+(?:\s+(?:[A-ZÀ-Þ][\w'’.-]+|de|da|van|von|der|del|la|le|y|bin|al-?\w*)){1,4}$")
INSTITUTION = re.compile(r"Universit|Department|School|Institute|College|NBER|CEPR|CESifo|IZA|Bank|Center|Centre|Foundation")


def pull(text, names=("thanks", "footnote")):
    r"""Remove \thanks{...}/\footnote{...} (balanced) and return (clean_text, [(pos, arg), ...])."""
    out, notes, i = [], [], 0
    rx = re.compile(r"\\(?:" + "|".join(names) + r")\s*(\[[^\]]*\])?\s*\{")
    while True:
        m = rx.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        arg, end = group(text, m.end() - 1)
        notes.append((len("".join(out)), arg))
        i = end
    return "".join(out), notes


def parse_contact(txt):
    r"""affiliation text, email, orcid, corresponding? from an \affil or \thanks note."""
    raw = txt.replace("\\_", "_")
    emails = re.findall(r"mailto:([^}\s]+)", raw) + EMAIL.findall(detex(re.sub(r"\\href\{[^}]*\}", "", raw)))
    t = detex(raw)
    orcid = ORCID.search(t)
    corr = bool(re.search(r"correspond", t, re.I))
    aff = EMAIL.sub("", ORCID.sub("", t))
    aff = re.sub(r"Corresponding author\.?|\bORCID\b:?|E-?mail\s*:?|PO Box[^.]*\.|\b\d{5}(-\d{4})?\b|"
                 r"(?:Tel|Phone|Fax)\.?:?\s*[\d()+\s.-]+", "", aff, flags=re.I)
    aff = re.sub(r"(\s*[.,;])+\s*$", "", re.sub(r"\.\s*\.", ".", aff))
    aff = re.sub(r"\s+", " ", aff).strip(" ,.;:")
    return aff if INSTITUTION.search(aff) else "", (emails[-1].replace("\\_", "_") if emails else ""), (orcid.group() if orcid else ""), corr


def new_author(name, src):
    parts = name.split()
    return {"name": name, "first_name": " ".join(parts[:-1]), "last_name": parts[-1], "email": "", "website": "",
            "orcid": "", "affiliation": "", "affiliation_short": "", "thanks": "", "corresponding": False, "sources": [src]}


def extract(tex_files):
    info = {"title": "", "subtitle": "", "authors": [], "acknowledgements": "", "sources": [], "confirmed": False}
    for tf in tex_files:
        t = strip_comments(read_text_retry(Path(tf)))
        src = f"tex:{Path(tf).name}"
        if not info["title"]:
            for _, arg in commands(t, "title"):
                clean, notes = pull(arg)
                info["acknowledgements"] = " ".join(detex(n) for _, n in notes)
                parts = [p.strip() for p in re.split(r"\\\\", clean) if detex(p)]
                if parts:
                    info["title"] = detex(parts[0])
                    info["subtitle"] = " ".join(detex(p) for p in parts[1:])
                    info["sources"].append(src)
                break
        affils = {lab.strip("[]").strip(): a for lab, a in commands(t, "affil")}
        for opt, arg in commands(t, "author"):
            clean, notes = pull(arg)
            # split the author block into name chunks; attach each note to the chunk it follows
            pieces = [(m.start(), m.end()) for m in re.finditer(r"[^,\n]+?(?=,|\\and\b|\\\\|\band\b|$)", clean)]
            for k, (a0, a1) in enumerate(pieces):
                name = detex(re.sub(r"^\s*and\s+", "", clean[a0:a1]))
                if not NAME_RX.match(name) or INSTITUTION.search(name):
                    continue
                if any(x["name"] == name for x in info["authors"]):
                    continue
                au = new_author(name, src)
                nxt = pieces[k + 1][0] if k + 1 < len(pieces) else len(clean) + 1
                mine = [n for pos, n in notes if a0 <= pos <= nxt] or ([n for _, n in notes] if len(pieces) == 1 else [])
                labels = [x.strip() for x in opt.strip("[]").split(",") if x.strip()]
                texts = mine + [affils[l] for l in labels if l in affils]
                for tx in texts:
                    aff, em, oc, corr = parse_contact(tx)
                    au["affiliation"] = au["affiliation"] or aff
                    au["email"] = au["email"] or em
                    au["orcid"] = au["orcid"] or oc
                    au["corresponding"] = au["corresponding"] or corr
                info["authors"].append(au)
        # acknowledgement \thanks outside \author (authblk style)
        if not info["acknowledgements"]:
            info["acknowledgements"] = " ".join(detex(a) for _, a in commands(t, "thanks")
                                                if re.search(r"thank|grateful|acknowledg|support", a, re.I))[:2000]
    return info


# ---------------------------------------------------------------- tokens
def join_and(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]


def tokens(info):
    A = info.get("authors", [])
    link_md = [f"[{a['name']}]({a['website']})" if a.get("website") else a["name"] for a in A]
    link_html = [f'<a href="{a["website"]}">{a["name"]}</a>' if a.get("website") else a["name"] for a in A]

    def thanks(a):
        bits = [a.get("affiliation", "")]
        if a.get("email"):
            bits.append(f"\\href{{mailto:{a['email']}}}{{{a['email'].replace('_', chr(92) + '_')}}}")
        if a.get("orcid"):
            bits.append(f"ORCID {a['orcid']}")
        s = ", ".join(b for b in bits if b)
        return s + (f". {a['thanks']}" if a.get("thanks") else "")
    cite = [f"{a.get('last_name') or a['name'].split()[-1]}, {a.get('first_name') or ' '.join(a['name'].split()[:-1])}" for a in A]
    c = info.get("compute", {})
    logos = info.get("logos", [])
    T = {
        "title": info.get("title", ""), "subtitle": info.get("subtitle", ""),
        "manuscript_id": info.get("manuscript_id", ""), "journal": info.get("journal", ""),
        "year": str(info.get("year", "")), "doi": info.get("doi", ""),
        "authors_and": join_and([a["name"] for a in A]),
        "authors_md": join_and(link_md),
        "authors_md_list": "\n".join(f"  - {x}" for x in link_md),
        "authors_html": join_and(link_html),
        "authors_citation": join_and(cite),
        "authors_latex": " \\and ".join(f"{a['name']}\\thanks{{{thanks(a)}}}" for a in A),
        "laptop_specs": c.get("laptop_specs", ""), "laptop_memory": c.get("laptop_memory", ""),
        "cluster_specs": c.get("cluster_specs", ""), "compute_hours": c.get("compute_hours", ""),
        "logos_md": " ".join(f'[<img src="{l["url"]}" width="{l.get("width", 200)}">]({l.get("link", "")})' for l in logos if l.get("url")),
    }
    # legacy single-author tokens (older templates): first/corresponding author
    lead = next((a for a in A if a.get("corresponding")), A[0] if A else {})
    T.update({"author_name": T["authors_and"], "author_last_name": lead.get("last_name", ""),
              "author_email": lead.get("email", ""), "author_website": lead.get("website", ""),
              "author_orcid": lead.get("orcid", ""), "author_affiliation": lead.get("affiliation", ""),
              "author_affiliation_short": lead.get("affiliation_short", ""), "author_affiliation_extra": "",
              "author_grants": lead.get("thanks", ""),
              "institution_logo_url": logos[0]["url"] if logos else "", "institution_logo_width": str(logos[0].get("width", 200)) if logos else "",
              "institution_logo_link": logos[0].get("link", "") if logos else ""})
    return T


# ---------------------------------------------------------------- CLI
def load(p):
    p = Path(p)
    return json.loads(read_text_retry(p)) if p.exists() else {"authors": [], "confirmed": False}


def save(p, info):
    p = assert_writable(Path(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge(info, new):
    for k, v in new.items():
        if k == "authors":
            for na in v:
                cur = next((a for a in info["authors"] if a["name"].lower() == na.get("name", "").lower()), None)
                if cur is None:
                    base = {"name": "", "first_name": "", "last_name": "", "email": "", "website": "", "orcid": "",
                            "affiliation": "", "affiliation_short": "", "thanks": "", "corresponding": False, "sources": []}
                    base.update(na)
                    if base["name"] and not base["last_name"]:
                        base["first_name"], base["last_name"] = " ".join(base["name"].split()[:-1]), base["name"].split()[-1]
                    info["authors"].append(base)
                else:
                    for kk, vv in na.items():
                        if kk == "sources":
                            cur["sources"] = list(dict.fromkeys(cur.get("sources", []) + vv))
                        elif vv not in ("", None):
                            cur[kk] = vv
        elif isinstance(v, dict) and isinstance(info.get(k), dict):
            info[k].update(v)
        else:
            info[k] = v
    info["confirmed"] = False if "authors" in new else info.get("confirmed", False)
    return info


def show(info):
    print(f"Title:    {info.get('title', '')}" + (f" — {info['subtitle']}" if info.get("subtitle") else ""))
    for k in ("manuscript_id", "journal", "year", "doi"):
        if info.get(k):
            print(f"{k:9s} {info[k]}")
    print(f"Authors ({len(info.get('authors', []))}):")
    missing = []
    for a in info.get("authors", []):
        print(f"  • {a['name']}{' (corresponding)' if a.get('corresponding') else ''}")
        for k in ("affiliation", "affiliation_short", "email", "website", "orcid"):
            print(f"      {k:18s} {a.get(k) or '—'}")
        print(f"      sources            {', '.join(a.get('sources', [])) or '—'}")
        missing += [f"{a['name']}: {k}" for k in REQUIRED_AUTHOR + RECOMMENDED_AUTHOR if not a.get(k)]
    c = info.get("compute", {})
    print(f"Compute: {c.get('laptop_specs') or '—'} | cluster: {c.get('cluster_specs') or '—'}")
    print(f"MISSING={'; '.join(missing)}")
    print(f"CONFIRMED_BY_USER={'yes' if info.get('confirmed') else 'no'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("--tex", action="append", required=True); e.add_argument("--out", required=True)
    s = sub.add_parser("set"); s.add_argument("--file", required=True); s.add_argument("--json", default=None)
    s.add_argument("--author", default=None); s.add_argument("--field", nargs="*", default=[])
    for name in ("show", "confirm", "tokens"):
        x = sub.add_parser(name); x.add_argument("--file", required=True)
    a = ap.parse_args()

    if a.cmd == "extract":
        info = extract(a.tex)
        save(a.out, info)
        show(info)
        print(f"✅ draft written to {a.out} — complete with web searches, then confirm with the user")
    elif a.cmd == "set":
        info = load(a.file)
        if a.json:
            merge(info, json.loads(a.json))
        if a.author:
            fields = {}
            for f in a.field:
                k, v = f.split("=", 1)
                if k in ("source", "sources"):
                    fields.setdefault("sources", []).append(v)
                else:
                    fields[k] = v
            if "corresponding" in fields:
                fields["corresponding"] = fields["corresponding"].lower() in ("1", "true", "yes")
            merge(info, {"authors": [dict(name=a.author, **fields)]})
        elif a.field:
            merge(info, dict(f.split("=", 1) for f in a.field))
        save(a.file, info)
        show(info)
    elif a.cmd == "show":
        show(load(a.file))
    elif a.cmd == "confirm":
        info = load(a.file)
        info["confirmed"] = True
        save(a.file, info)
        print("✅ authors confirmed by the user")
    elif a.cmd == "tokens":
        print(json.dumps(tokens(load(a.file)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
