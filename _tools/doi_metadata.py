#!/usr/bin/env python3
"""Fetch Crossref metadata for every publication that has a DOI.

Usage: python3 _tools/doi_metadata.py _data/cv/publications.yml OUT.json

Also looks up DOIs in _data/cv_new/publications.yml (items from the Add form),
if that file exists next to the folder holding publications.yml.

Writes one record per DOI: title, authors ("Family, G. I.; ..."), venue,
year, volume, issue, pages, publisher and Crossref type. It never edits
publications.yml; a person (or Claude) reviews the JSON and merges it.
Runs in GitHub Actions, which can reach api.crossref.org.
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path
import yaml

UA = "david-i-schwartz.github.io publications tools (mailto:David.I.Schwartz@rit.edu)"

def initials(given):
    parts = [p for p in given.replace("-", " -").split() if p]
    out = []
    for p in parts:
        if p.startswith("-"):
            out.append("-" + p[1:2] + ".")
        else:
            out.append(p[0] + ".")
    return " ".join(out).replace(" -", "-")

def fetch(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/()")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["message"]

def main(src, out):
    pubs = yaml.safe_load(open(src, encoding="utf-8")) or []
    new_path = Path(src).resolve().parent.parent / "cv_new" / "publications.yml"
    if new_path.exists():
        pubs += [p for p in (yaml.safe_load(open(new_path, encoding="utf-8")) or []) if isinstance(p, dict)]
    dois = sorted({str(p["doi"]).strip().lower() for p in pubs if p.get("doi")})
    result = {}
    for doi in dois:
        try:
            m = fetch(doi)
        except Exception as e:  # keep going; report what failed
            result[doi] = {"error": str(e)}
            continue
        authors = []
        for a in m.get("author", []):
            fam = a.get("family") or a.get("name") or ""
            giv = initials(a.get("given", "")) if a.get("given") else ""
            authors.append(f"{fam}, {giv}".strip(", "))
        issued = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
        result[doi] = {
            "title": (m.get("title") or [""])[0],
            "authors": "; ".join(authors),
            "venue": (m.get("container-title") or [""])[0] or (m.get("event", {}) or {}).get("name", ""),
            "year": issued,
            "volume": m.get("volume", ""),
            "issue": m.get("issue", ""),
            "pages": m.get("page", ""),
            "publisher": m.get("publisher", ""),
            "crossref_type": m.get("type", ""),
            "isbn": (m.get("ISBN") or [""])[0],
        }
        time.sleep(0.2)
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    bad = [d for d, v in result.items() if "error" in v]
    print(f"{len(result)} DOIs, {len(bad)} failed: {bad}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
