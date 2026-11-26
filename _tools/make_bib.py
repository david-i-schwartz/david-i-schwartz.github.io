#!/usr/bin/env python3
"""Write a BibTeX file of Dave's publications from the site data.

Usage:
  python3 _tools/make_bib.py _data/cv/publications.yml _data/cv/orcid_types.yml OUT.bib
  python3 _tools/make_bib.py ... OUT.bib --only KEYS.txt   (one entry key per line)

The site build runs the first form, so https://david-i-schwartz.github.io/publications.bib
always matches publications.yml. The second form makes a smaller file, such as a
one-time ORCID import of the entries ORCID doesn't have yet.

Items added through the "Add · Publication" form in Pages CMS live in
_data/cv_new/publications.yml (next to the folder holding publications.yml).
This script picks that file up on its own and writes those items first. They
have no number yet, so their BibTeX key is schwartz-<type>-new-<year>-<hash of
the citation>; the key changes to the usual numbered one when Claude folds the
item into publications.yml.

Each entry's BibTeX type follows its ORCID work type (orcid_type, or the
default for its section in orcid_types.yml), because ORCID's BibTeX import
picks the work type from the entry type: article -> journal article,
inproceedings -> conference paper, incollection -> book chapter, book -> book,
techreport -> report, misc -> other. Talks, games and creative works have no
matching BibTeX type, so they go in as misc and arrive on ORCID as "Other".
"""
import hashlib, re, sys
from pathlib import Path
import yaml

# ORCID work type -> (BibTeX entry type, field that holds the venue)
BIBTYPE = {
    "journal-article": ("article", "journal"),
    "magazine-article": ("article", "journal"),
    "conference-paper": ("inproceedings", "booktitle"),
    "book-chapter": ("incollection", "booktitle"),
    "book": ("book", "publisher"),
    "report": ("techreport", "institution"),
}
DEFAULT = ("misc", "howpublished")

def key_for(p):
    kind = str(p.get("type") or "other").replace("_", "-")
    if p.get("number") not in (None, ""):
        return f"schwartz-{kind}-{p['number']}"
    # A new item from the Add form has no number yet: use a short, stable
    # fingerprint of its citation so the key survives other items being added.
    fp = hashlib.sha1(str(p.get("citation") or p.get("title") or "").encode("utf-8")).hexdigest()[:6]
    return f"schwartz-{kind}-new-{p.get('year') or 'undated'}-{fp}"

def load_new(master_path):
    """Items from the Add form: <data dir>/cv_new/publications.yml, if it exists."""
    path = Path(master_path).resolve().parent.parent / "cv_new" / "publications.yml"
    if not path.exists():
        return []
    items = yaml.safe_load(open(path, encoding="utf-8")) or []
    return [p for p in items if isinstance(p, dict)]

def esc(s):
    """Make free text safe inside a braced BibTeX field."""
    s = re.sub(r"\s+", " ", str(s)).strip()
    s = s.replace("\\", "").replace("{", "").replace("}", "")
    for ch in "&%#$_":
        s = s.replace(ch, "\\" + ch)
    return s

def authors(s):
    names = [a.strip() for a in str(s).split(";") if a.strip()]
    return " and ".join(esc(n) for n in names)

def entry(p, types):
    otype = p.get("orcid_type") or types.get(p.get("type"), "")
    btype, vfield = BIBTYPE.get(otype, DEFAULT)
    fields = []
    title = p.get("title")
    note = None
    if not title:  # a new entry nobody has split yet: fall back to the citation
        title = p.get("citation", "")
        note = "no title field in publications.yml; citation used as title"
    fields.append(("title", esc(title)))
    if p.get("authors"):
        fields.append(("author", authors(p["authors"])))
    if p.get("venue"):
        fields.append((vfield, esc(p["venue"])))
    if p.get("year"):
        fields.append(("year", esc(p["year"])))
    doi = str(p.get("doi") or "").strip()
    if doi:
        fields.append(("doi", doi.replace("{", "").replace("}", "")))
    link = str(p.get("link") or "").strip()
    if link.startswith(("http://", "https://")) and "doi.org/" not in link:
        fields.append(("url", link.replace("{", "").replace("}", "")))
    lines = [f"@{btype}{{{key_for(p)},"]
    if note:
        lines.insert(0, f"% {note}")
    lines += [f"  {k} = {{{v}}}," for k, v in fields]
    lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)

def main(argv):
    if len(argv) not in (4, 6) or (len(argv) == 6 and argv[4] != "--only"):
        sys.exit(__doc__)
    pubs = load_new(argv[1]) + (yaml.safe_load(open(argv[1], encoding="utf-8")) or [])
    types = yaml.safe_load(open(argv[2], encoding="utf-8")) or {}
    only = None
    if len(argv) == 6:
        only = [l.strip() for l in open(argv[5], encoding="utf-8") if l.strip() and not l.startswith("#")]
        known = {key_for(p) for p in pubs}
        missing = [k for k in only if k not in known]
        if missing:
            sys.exit(f"unknown keys: {missing}")
    chosen = [p for p in pubs if only is None or key_for(p) in only]
    if only is not None:  # keep the order of the keys file
        chosen.sort(key=lambda p: only.index(key_for(p)))
    head = ("% Publications of David I. Schwartz (ORCID 0000-0002-1675-9535)\n"
            "% Generated from _data/cv/publications.yml and _data/cv_new/publications.yml; edit those, not this file.\n\n")
    with open(argv[3], "w", encoding="utf-8") as f:
        f.write(head + "\n\n".join(entry(p, types) for p in chosen) + "\n")
    print(f"{len(chosen)} entries -> {argv[3]}")

if __name__ == "__main__":
    main(sys.argv)
