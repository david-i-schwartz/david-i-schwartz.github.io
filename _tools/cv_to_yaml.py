#!/usr/bin/env python3
"""Convert the extracted-CV markdown (HTML tables + bullets) into Jekyll _data/cv/*.yml files.

Usage: python3 cv_to_yaml.py [input.md] [output_dir]
"""
import re
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/claude/cv/schwartz-cv-2026-09-03.md")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/home/claude/site/_data/cv")
OUT.mkdir(parents=True, exist_ok=True)

TEXT = SRC.read_text(encoding="utf-8")
LINES = TEXT.split("\n")

# --------------------------------------------------------------------------------------
# Obvious PDF-extraction glitches (missing/extra spaces). Applied to every cell/bullet.
# --------------------------------------------------------------------------------------
GLITCH_FIXES = [
    ("Universit y of South Florida", "University of South Florida"),
    ("inAcademic", "in Academic"),
    ("ALarge", "A Large"),
    ("finalreport", "final report"),
    ("andGame-Development", "and Game-Development"),
    ("October2002", "October 2002"),
    ("Washington,DC", "Washington, DC"),
    ("Sci-FiConvention", "Sci-Fi Convention"),
    ("Interfaces,Dakota", "Interfaces, Dakota"),
    ("AirForce Materiel", "Air Force Materiel"),
    ("Geneseo,NY", "Geneseo, NY"),
    ("studentsmake", "students make"),
    ("$22Kgrant", "$22K grant"),
    ("Physical Computing2,", "Physical Computing 2,"),
    ("game design.gdiac.cis.cornell.edu", "game design. gdiac.cis.cornell.edu"),
    ("(capstone chair).Yana", "(capstone chair). Yana"),
    ("Stephen Oyarijivbie. Justin Schwartz.", "Stephen Oyarijivbie, Justin Schwartz."),
    ("McCarthy, P.(2015)", "McCarthy, P. (2015)"),
    ("Bronson, G.(2005)", "Bronson, G. (2005)"),
    ("Pan, Y.(2016)", "Pan, Y. (2016)"),
    ("2026– present", "2026–present"),
    ("2024– present", "2024–present"),
    ("Rochester Institute of Technology Golisano College", "Rochester Institute of Technology, Golisano College"),
    ("06–09, 2008 05–08, 2007 06–12, 2006", "06–09, 2008; 05–08, 2007; 06–12, 2006"),
    ("Excellence in Teaching I withdrew", "Excellence in Teaching. I withdrew"),
]


def clean(s: str) -> str:
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    for a, b in GLITCH_FIXES:
        s = s.replace(a, b)
    return s


def section(start_pat: str, end_pat: str) -> str:
    """Return the text between the first line matching start_pat (inclusive) and the next
    line matching end_pat (exclusive)."""
    start = next(i for i, l in enumerate(LINES) if re.match(start_pat, l))
    end = next((i for i in range(start + 1, len(LINES)) if re.match(end_pat, LINES[i])), len(LINES))
    return "\n".join(LINES[start:end])


class Cell:
    def __init__(self, text, colspan=1, rowspan=1, carried=False):
        self.text = text
        self.colspan = colspan
        self.rowspan = rowspan
        self.carried = carried

    def __repr__(self):
        return f"Cell({self.text!r}{', carried' if self.carried else ''}{', cs=' + str(self.colspan) if self.colspan > 1 else ''})"


def parse_tables(text: str):
    """Parse every <table> in text. Returns a list of tables; each table is a list of rows;
    each row is a list of Cell objects in logical column order with rowspans resolved
    (carried cells are copies of the cell from the row above, flagged carried=True)."""
    tables = []
    for m in re.finditer(r"<table>(.*?)</table>", text, flags=re.S):
        soup = BeautifulSoup("<table>" + m.group(1) + "</table>", "html.parser")
        rows = []
        pending = {}  # col index -> [Cell, remaining_rows]
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            cells = []
            col = 0
            tds_iter = iter(tds)
            while True:
                if col in pending:
                    c, remaining = pending[col]
                    cells.append(Cell(c.text, c.colspan, 1, carried=True))
                    remaining -= 1
                    if remaining <= 0:
                        del pending[col]
                    else:
                        pending[col][1] = remaining
                    col += c.colspan
                    continue
                td = next(tds_iter, None)
                if td is None:
                    # Any pending cells further right?
                    further = [k for k in pending if k > col]
                    if further:
                        col = min(further)
                        continue
                    break
                cs = int(td.get("colspan", 1))
                rs = int(td.get("rowspan", 1))
                c = Cell(clean(td.get_text(" ")), cs, rs)
                cells.append(c)
                if rs > 1:
                    pending[col] = [c, rs - 1]
                col += cs
            rows.append(cells)
        tables.append(rows)
    return tables


def own_content(row):
    return any(c.text for c in row if not c.carried)


class Quoted(str):
    """String that is always emitted single-quoted (so Jekyll/Psych never reads it as a number)."""


yaml.SafeDumper.add_representer(Quoted, lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", str(v), style="'"))
NUMERIC_LOOKING = re.compile(r"^[\d,.\s–-]+$")


def quote_numeric_like(obj):
    if isinstance(obj, dict):
        return {k: quote_numeric_like(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [quote_numeric_like(v) for v in obj]
    if isinstance(obj, str) and obj and NUMERIC_LOOKING.match(obj):
        return Quoted(obj)
    return obj


def dump(name, data):
    path = OUT / name
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(quote_numeric_like(data), f, allow_unicode=True, sort_keys=False, width=1000)
    n = len(data) if isinstance(data, list) else {k: len(v) for k, v in data.items()}
    print(f"wrote {path}: {n}")


YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def split_org_location(s: str):
    m = re.match(r"^(.*?)\s*((?:Rochester|Ithaca|Amherst|Rome|Buffalo), (?:New York|Illinois|NY))$", s)
    if m:
        return m.group(1).strip(), m.group(2)
    if s in ("Rochester, New York", "Chicago, Illinois"):
        return "", s
    return s, ""


# ======================================================================================
# 1. positions.yml
# ======================================================================================
def build_positions():
    sec = section(r"^<table><tr> <td colspan=4> 1\. Career History", r"^<table><tr> <td colspan=6> 2\. Education")
    table = parse_tables(sec)[0]
    group_map = {"Academia: Faculty": "Faculty", "Academia: Administration": "Administration",
                 "Government": "Government", "Industry": "Industry"}
    out = []
    group = None
    for row in table:
        if len(row) == 1:
            t = row[0].text
            if t.startswith("1. Career History"):
                continue
            group = group_map[t]
            continue
        years, title = row[0].text, row[1].text
        if group == "Industry":
            unit, org, loc = "", row[2].text, row[3].text
        elif len(row) == 3:  # colspan=2 cell: organization + location
            unit = ""
            org, loc = split_org_location(row[2].text)
        else:
            unit = row[2].text
            org, loc = split_org_location(row[3].text)
        out.append({"group": group, "years": years, "title": title, "unit": unit,
                    "organization": org, "location": loc})
    return out


# ======================================================================================
# 2. education.yml
# ======================================================================================
def build_education():
    sec = section(r"^<table><tr> <td colspan=6> 2\. Education", r"^# 3\. ")
    table = parse_tables(sec)[0]
    out = []
    for row in table:
        if len(row) == 1:
            continue
        out.append({"year": row[0].text, "degree": row[1].text, "field": row[2].text,
                    "focus": row[3].text, "institution": row[4].text, "location": row[5].text})
    return out


# ======================================================================================
# 3. administration.yml
# ======================================================================================
def build_administration():
    sec = section(r"^# 3\. ", r"^# 4\. ")
    out = []
    cur = None
    for line in sec.split("\n"):
        m = re.match(r"^## 3\.\d+\s+(.*)$", line)
        if m:
            heading = clean(m.group(1))
            years = ""
            ym = re.search(r"\(([^()]*?)((?:19|20)\d{2}–(?:(?:19|20)\d{2}|present))\)\s*$", heading)
            if ym:
                years = ym.group(2)
                prefix = ym.group(1).rstrip(", ").strip()
                heading = heading[: ym.start()].rstrip()
                if prefix:
                    heading = f"{heading} ({prefix})"
            cur = {"role": heading, "years": years, "highlights": []}
            out.append(cur)
        elif line.startswith("•") and cur is not None:
            cur["highlights"].append(clean(line[1:]))
    return out


# ======================================================================================
# 4. funding.yml
# ======================================================================================
def to_amount(s: str):
    s2 = s.replace("$", "").replace(",", "").strip()
    if re.fullmatch(r"\d+(\.\d+)?", s2):
        return float(s2) if "." in s2 else int(s2)
    return s


def build_funding():
    sec41 = section(r"^## 4\.1 ", r"^## 4\.2 ")
    summary = []
    for row in parse_tables(sec41)[0]:
        if row[0].text == "Location":
            continue
        summary.append({"location": row[0].text, "funding_k": to_amount(row[1].text),
                        "career_total_k": to_amount(row[2].text)})

    grants = []
    legend = ""
    # 4.2 post-tenure: Date | Funding ($K) | Total Since Tenure ($K) | Source | Role | Title
    sec42 = section(r"^## 4\.2 ", r"^## 4\.3 ")
    for row in parse_tables(sec42)[0]:
        if len(row) == 1:
            legend = row[0].text
            continue
        if row[0].text == "Date":
            continue
        years = row[0].text
        notes = [f"Total since tenure ($K): {row[2].text}"]
        if not years:
            years = "2022"
            notes.append("Year cell is blank in the source table; 2022 inferred from table position and running total.")
        grants.append({"period": "RIT post-tenure", "years": years, "title": row[5].text,
                       "sponsor": row[3].text, "role": row[4].text, "amount_k": to_amount(row[1].text),
                       "notes": "; ".join(notes)})
    # 4.3 pre-tenure: Date | Funding ($K) | Total ($K) | Source | Role | Title
    sec43 = section(r"^## 4\.3 ", r"^## 4\.4 ")
    for row in parse_tables(sec43)[0]:
        if row[0].text == "Date":
            continue
        grants.append({"period": "RIT pre-tenure", "years": row[0].text, "title": row[5].text,
                       "sponsor": row[3].text, "role": row[4].text, "amount_k": to_amount(row[1].text),
                       "notes": f"Running pre-tenure total ($K): {row[2].text}"})
    # 4.4 Cornell: Dates | Funding ($K) | Source | Role | Notes
    sec44 = section(r"^## 4\.4 ", r"^# 5\. ")
    for row in parse_tables(sec44)[0]:
        if row[0].text == "Dates":
            continue
        grants.append({"period": "Cornell", "years": row[0].text, "title": "",
                       "sponsor": row[2].text, "role": row[3].text, "amount_k": to_amount(row[1].text),
                       "notes": row[4].text})
    return {"legend": legend, "summary": summary, "grants": grants}


# ======================================================================================
# 5. publications.yml
# ======================================================================================
URL_RE = re.compile(r"(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.(?:edu|com|org|net|biz|html)(?:/[^\s,)]*)?")


def find_url(s: str):
    m = re.search(r"(?:https?://|www\.)[^\s]+", s)
    if m:
        return m.group(0).rstrip(".,;")
    return None


PUB_SECTIONS = [
    (r"^## 5\.2 Peer-Reviewed Books", r"^## 5\.3 Peer-Reviewed Journal", "book_or_chapter"),
    (r"^## 5\.3 Peer-Reviewed Journal", r"^## 5\.4 Shipped", "journal"),
    (r"^## 5\.4 Shipped", r"^## 5\.5 Additional Creative", "game_or_simulation"),
    (r"^## 5\.5 Additional Creative", r"^## 5\.6 Peer-Reviewed Conference", "creative_work"),
    (r"^## 5\.6 Peer-Reviewed Conference", r"^## 5\.7 Peer-Reviewed Abstracts", "conference_paper"),
    (r"^## 5\.7 Peer-Reviewed Abstracts", r"^## 5\.1 Invited", "peer_reviewed_abstract_or_talk"),
    (r"^## 5\.1 Invited", r"^## 5\.2 Sponsor-Reviewed", "invited_talk"),
    (r"^## 5\.2 Sponsor-Reviewed", r"^## 5\.3 Popular Press", "sponsor_reviewed_report"),
]


def build_publications():
    out = []
    for start, end, ptype in PUB_SECTIONS:
        sec = section(start, end)
        for table in parse_tables(sec):
            for row in table:
                if not own_content(row):
                    continue
                if len(row) == 4:
                    number, year, link, citation = (c.text for c in row)
                elif len(row) == 3:
                    number, year, citation = (c.text for c in row)
                    link = ""
                else:
                    raise ValueError(f"unexpected pub row {row}")
                item = {"type": ptype, "number": int(number), "year": year, "citation": citation}
                url = find_url(link)
                if url:
                    item["link"] = url
                out.append(item)
    return out


# ======================================================================================
# 6. press.yml
# ======================================================================================
KNOWN_OUTLETS = [
    "RIT News", "Cornell University", "Government Technology", "Rochester Business Journal", "Inverse",
    "CNET", "Gearfuse", "Hackaday", "The Cornell Daily Sun", "Cornell Chronicle", "Bloomberg",
    "Ithaca College News", "Gamesauce", "WPBS", "The Crispy Noodle", "Nextstar Inc.", "Research at RIT",
    "The Conversation",
]


def build_press():
    out = []
    # Popular press table: # | year | Link | citation
    sec = section(r"^## 5\.3 Popular Press", r"^## 5\.4 Recent Articles")
    for row in parse_tables(sec)[0]:
        item = {"kind": "popular_press", "number": int(row[0].text), "year": row[1].text,
                "title_or_citation": row[3].text}
        url = find_url(row[3].text)
        if url:
            item["url"] = url
        for o in KNOWN_OUTLETS:
            if o in row[3].text:
                item["outlet"] = o
                break
        out.append(item)
    # Recent news table: # | year | Link | title | byline
    sec = section(r"^## 5\.4 Recent Articles", r"^## 5\.5 Additional Articles")
    for row in parse_tables(sec)[0]:
        byline = row[4].text
        author, outlet = (byline.rsplit(", ", 1) + [""])[:2] if ", " in byline else ("", byline)
        item = {"kind": "news", "number": int(row[0].text), "year": row[1].text,
                "title_or_citation": row[3].text, "author": author, "outlet": outlet}
        out.append(item)
    # Additional news bullets
    sec = section(r"^## 5\.5 Additional Articles", r"^# 6\. ")
    bullets = []
    for line in sec.split("\n")[1:]:
        line = line.strip()
        if not line:
            continue
        if line.startswith("•"):
            bullets.append(line[1:].strip())
        elif line.startswith("### "):
            bullets[-1] += " " + line[4:].strip()  # stray heading = continuation of the previous bullet
        else:
            bullets[-1] += " " + line  # wrapped line
    for b in bullets:
        b = clean(b)
        m = re.match(r"^\((\d{4})\)\s*(.*)$", b)
        year, rest = (m.group(1), m.group(2)) if m else ("", b)
        item = {"kind": "news", "year": year}
        url = None
        trailing = ""
        um = re.search(r"(?:https?://|www\.|(?:[a-z0-9-]+\.)+(?:com|net|org|edu|biz)/)[^\s]+", rest)
        if um:
            url = um.group(0).rstrip(".,")
            rest_wo = rest[: um.start()].rstrip(" ,")
            trailing = rest[um.end():].strip(" .,")
        else:
            rest_wo = rest
        item["title_or_citation"] = rest_wo
        if trailing:
            item["notes"] = trailing
        outlet = ""
        for o in KNOWN_OUTLETS:
            if re.search(re.escape(o) + r"(,|\s*$)", rest_wo):
                outlet = o
                break
        if outlet:
            item["outlet"] = outlet
        if url:
            item["url"] = url
        if "(link defunct)" in rest:
            item["link_status"] = "defunct"
        out.append(item)
    return out


# ======================================================================================
# 7. teaching.yml
# ======================================================================================
def build_teaching():
    sec61 = section(r"^## 6\.1 Terminology", r"^## 6\.2 ")
    notes = [clean(l) for l in sec61.split("\n")[1:] if l.strip() and not l.startswith("<")]
    terminology = []
    for row in parse_tables(sec61)[0]:
        if row[0].text == "Degree":
            continue
        terminology.append({"code": row[0].text, "meaning": row[1].text, "institution": row[2].text})

    dev, taught, by_term = [], [], []
    inst_secs = [
        ("Rochester Institute of Technology", section(r"^## 6\.2 ", r"^## 6\.3 ")),
        ("Cornell University", section(r"^## 6\.3 ", r"^## 6\.4 ")),
        ("State University of New York at Buffalo", section(r"^## 6\.4 ", r"^# 7\. ")),
    ]
    for inst, sec in inst_secs:
        for table in parse_tables(sec):
            for row in table:
                if not own_content(row):
                    continue
                if len(row) == 1:
                    continue  # header band
                texts = [c.text for c in row]
                if len(texts) == 3 and YEAR_RE.search(texts[1]) and len(texts[2]) > 40:
                    dev.append({"institution": inst, "course": texts[0], "years": texts[1], "description": texts[2]})
                elif len(texts) == 3:
                    taught.append({"institution": inst, "course": texts[0], "title": texts[1], "terms": texts[2]})
                elif len(texts) == 2:
                    by_term.append({"institution": inst, "term": texts[0], "courses": texts[1]})
                else:
                    raise ValueError(f"unexpected teaching row {row}")
        # Stray plain-text rows outside tables (e.g. "F99 CS 100B, CS 144")
        for line in sec.split("\n"):
            m = re.match(r"^([FS]\d{2})\s+(.+)$", line.strip())
            if m:
                by_term.append({"institution": inst, "term": m.group(1), "courses": clean(m.group(2))})
    return {"terminology_notes": notes, "terminology": terminology, "course_development": dev,
            "courses_taught": taught, "courses_by_term": by_term}


# ======================================================================================
# 8. theses.yml
# ======================================================================================
ROLE_RE = re.compile(r"\((committee member|capstone chair|committee co-chair)\)")


THESIS_KEYS = ["years", "year", "student", "title", "type", "unit", "role", "institution", "notes"]


def thesis_item(**kw):
    return {k: kw.get(k, "") for k in THESIS_KEYS}


def parse_thesis_line(text, years):
    """'Title (YYYY). Type, Unit, Institution (role). Students. Extra.'"""
    item = thesis_item(years=years, institution="RIT")
    m = re.match(r"^(.*?)\s*\((\d{4})\)[.,]\s*(.*)$", text)
    if not m:
        item["title"] = text
        item["notes"] = "Unparsed; full text kept in title."
        return item
    item["title"], item["year"], rest = m.group(1), m.group(2), m.group(3)
    rm = ROLE_RE.search(rest)
    if rm:
        item["role"] = rm.group(1)
        desc = rest[: rm.start()].strip().rstrip(",")
        after = rest[rm.end():].lstrip(".: ").strip()
    else:
        desc, after = rest, ""
    # desc e.g. "MS Thesis and Capstone Project, IGM, RIT" / "MS Thesis, Cornell University"
    parts = [p.strip() for p in desc.split(",")]
    item["type"] = parts[0]
    if "Cornell" in desc:
        item["institution"] = "Cornell University"
    unit = [p for p in parts[1:] if p not in ("RIT", "Cornell University")]
    if unit:
        item["unit"] = ", ".join(unit)
    # after: "Students. Extra notes."
    if after:
        sentences = re.split(r"(?<=\.)\s+(?=[A-Z0-9])", after)
        item["student"] = sentences[0].rstrip(".").strip()
        if len(sentences) > 1:
            item["notes"] = " ".join(sentences[1:]).strip()
        # "Name, Professor of ..., url" -> keep affiliation in notes
        am = re.match(r"^([^,]+),\s*(Professor .*)$", item["student"])
        if am:
            item["student"] = am.group(1)
            item["notes"] = (am.group(2) + (" " + item["notes"] if item["notes"] else "")).strip()
    return item


def build_theses():
    sec = section(r"^# 7\. ", r"^# 8\. ")
    out = []
    years = None
    group = None  # for the 2022–present nested lists
    for raw in sec.split("\n")[1:]:
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^#+\s+(\d{4}–(?:\d{4}|present))\s*$", line)
        if m:
            years = m.group(1)
            group = None
            continue
        if line.startswith("▪"):
            body = clean(line[1:])
            if body.endswith(":"):
                group = body.rstrip(":")
                continue
            out.append(parse_thesis_line(body, years))
        elif line.startswith("•") and group:
            body = clean(line[1:])
            gtype = "Ph.D. dissertation" if "Ph.D." in group else "MS capstone"
            grole = "committee member"
            # "Name, Title (status)." or "Name, TBA."
            nm = re.match(r"^([^,]+),\s*(.*)$", body)
            student, rest = nm.group(1).strip(), nm.group(2).strip()
            notes = ""
            pm = re.search(r"\s*\(([^()]*(?:graduation|defense|\d{4}–\d{4})[^()]*)\)\.?\s*$", rest)
            if pm:
                notes = pm.group(1)
                rest = rest[: pm.start()].strip()
            title = rest.rstrip(".").strip()
            out.append(thesis_item(years=years, student=student, title=title, type=gtype, role=grole,
                                   institution="RIT", notes=notes))
    return out


# ======================================================================================
# 9. service.yml
# ======================================================================================
ROLE_WORDS = [
    "co-chair", "Co-chair", "Co-Chair", "chair", "Chair", "member", "Member", "advisor", "co-advisor",
    "presenter", "faculty supervisor", "ad-hoc", "Vice Chair", "Conference Chair", "Session Chair for Game Track",
    "IGM coordinator", "site organizer", "RIT organizer", "Planning Committee", "Lifetime Membership",
    "decade membership", "Faculty Advisor", "Faculty Co-advisor and founder", "Director and Founder",
    "Coordinator", "Vice President", "Leader", "Associate Editor", "Guest editor", "Co-editor",
    "Competition Judge", "Academic Program Reviewer", "Organizer", "Co-Director", "Director",
    "Undergraduate Program Coordinator", "Originator and Coordinator", "Site Coordinator", "Industry Liaison",
    "Expert interview",
]
YEARS_TOKEN = r"(?:19|20)\d{2}(?:[–-](?:(?:19|20)\d{2}|present|current))?"


def extract_years(text):
    """Pull all year/range tokens out of text; return (years_string, remaining_text)."""
    found = []
    def repl(m):
        found.append(m.group(1))
        return ""
    # parenthesised
    text = re.sub(r"\s*\((" + YEARS_TOKEN + r"(?:,\s*" + YEARS_TOKEN + r")*)\)", repl, text)
    # trailing after comma
    text = re.sub(r",\s*(" + YEARS_TOKEN + r")(?=\s*(?:;|$))", repl, text)
    # inline ", 2011–2016" followed by more text (rare) - leave
    text = re.sub(r"\s+;", ";", text).strip().rstrip(",;: ").strip()
    text = re.sub(r"\s{2,}", " ", text)
    return "; ".join(found), text


def parse_service_bullet(text, scope):
    item = {"scope": scope, "years": "", "role": "", "organization": "", "notes": ""}
    if scope == "RIT – Hosted Colloquia":
        item["role"] = "Host"
        m = re.match(r"^(.*?)\s*\((\d{4})\),?\s*(.*)$", text)
        if m and m.group(3) and not m.group(3).startswith("("):
            item["years"], item["organization"], item["notes"] = m.group(2), m.group(1), m.group(3)
        else:
            years, body = extract_years(text)
            parts = body.split(", ", 1)
            item["years"], item["organization"] = years, parts[0]
            item["notes"] = parts[1] if len(parts) > 1 else ""
        return item
    years, body = extract_years(text)
    item["years"] = years
    # hand-mapped odd bullets
    if body.startswith("Initiated and named portfolios.rit.edu"):
        item["organization"] = "portfolios.rit.edu"
        item["role"] = "Initiated and named"
        item["notes"] = body.split(", ", 1)[1]
        return item
    if body.startswith("Assisting "):
        item["organization"] = body
        return item
    if body.startswith("Leader of the "):
        item["role"], item["organization"] = "Leader", body[len("Leader of the "):]
        return item
    if ": " in body:
        before, after = body.split(": ", 1)
        if before == "ImagineRIT":
            item["organization"], item["notes"] = before, after
            return item
        if re.match(r"^(?:co-)?(?:chair|member|advisor)\b", after, re.I) and "," not in before:
            item["organization"], item["role"] = before.strip(), after.strip()
            return item
    segs = [s.strip() for s in body.split(", ")]
    # leading role ("Faculty Advisor, X", "Coordinator, X", "Associate Editor, X" ...)
    for rw in ROLE_WORDS:
        if segs[0].lower() == rw.lower():
            item["role"] = segs[0]
            item["organization"] = ", ".join(segs[1:])
            return item
    if re.match(r"^(Paper reviews? for|Article reviews? for|Chapter reviews? for|Textbook reviews? for|Expert interview on)", segs[0]):
        item["role"] = segs[0]
        item["organization"] = ", ".join(segs[1:])
        return item
    # trailing role ("X, Y, co-chair")
    last = segs[-1]
    if len(segs) > 1 and (any(last.lower() == rw.lower() for rw in ROLE_WORDS)
                          or re.match(r"^(?:co-)?(?:chair|member|advisor|organizer)\b", last, re.I)):
        item["role"] = last
        item["organization"] = ", ".join(segs[:-1])
        return item
    m = re.match(r"^(.*?)\s+(site organizer)$", body)
    if m:
        item["organization"], item["role"] = m.group(1), m.group(2)
        return item
    m = re.match(r"^(.*?)\s+\((RIT organizer)\)$", body)
    if m:
        item["organization"], item["role"] = m.group(1), m.group(2)
        return item
    item["organization"] = body
    return item


def build_service():
    sec = section(r"^# 8\. ", r"^# 9\. ")
    out = []
    # Leadership summary table
    for row in parse_tables(sec)[0]:
        if len(row) == 1:
            continue
        out.append({"scope": "RIT – Leadership Summary", "years": row[0].text, "role": row[1].text,
                    "organization": row[2].text.rstrip(","), "notes": ""})
    scope_map = {
        ("8.1", "Institute Committees/Task Forces and Related Service"): "RIT – Institute",
        ("8.1", "College Committees and Related Service"): "RIT – College",
        ("8.1", "Unit Committees and Related Service"): "RIT – Unit",
        ("8.1", "Student Organizations"): "RIT – Student Organizations",
        ("8.1", "Hosted Colloquia (college and unit)"): "RIT – Hosted Colloquia",
        ("8.2", None): "Regional and Local Community",
        ("8.3", "Professional Organizations"): "Field – Professional Organizations",
        ("8.3", "Professional Reviews"): "Field – Professional Reviews",
        ("8.3", "External Organizations, Conferences, and Events"): "Field – External Organizations, Conferences, and Events",
        ("8.4", "Leadership"): "Cornell – Leadership",
        ("8.4", "Student Organizations"): "Cornell – Student Organizations",
        ("8.4", "Computing Committees"): "Cornell – Computing Committees",
        ("8.4", "Admissions"): "Cornell – Admissions",
    }
    sub, subsub = None, None
    for raw in sec.split("\n"):
        line = raw.strip()
        m = re.match(r"^## (8\.\d)\s", line)
        if m:
            sub, subsub = m.group(1), None
            continue
        m = re.match(r"^### (.*)$", line)
        if m:
            subsub = m.group(1).strip()
            continue
        if line.startswith("•"):
            scope = scope_map[(sub, subsub)]
            out.append(parse_service_bullet(clean(line[1:]), scope))
    return out


# ======================================================================================
# 10. awards.yml
# ======================================================================================
AWARD_ORGS = ["I/ITSEC", "RIT Student Government", "ImagineRIT", "RPI GameFest", "Severed Short Film Night",
              "Games4Girls", "MTVU", "HiddenAgenda.com", "GCCIS", "Provost"]


def build_awards():
    sec = section(r"^# 9\. ", r"(?!x)x")  # runs to end of file
    out = []
    for row in parse_tables(sec)[0]:
        text = row[1].text
        org = next((o for o in AWARD_ORGS if o in text), "")
        if org == "Provost":
            org = "RIT Provost"
        year = ", ".join(row[0].text.split()) if re.fullmatch(r"(\d{4}\s+)+\d{4}", row[0].text) else row[0].text
        item = {"year": year, "title": text, "organization": org, "notes": ""}
        url = find_url(text)
        if url:
            item["notes"] = url
        out.append(item)
    return out


if __name__ == "__main__":
    dump("positions.yml", build_positions())
    dump("education.yml", build_education())
    dump("administration.yml", build_administration())
    dump("funding.yml", build_funding())
    dump("publications.yml", build_publications())
    dump("press.yml", build_press())
    dump("teaching.yml", build_teaching())
    dump("theses.yml", build_theses())
    dump("service.yml", build_service())
    dump("awards.yml", build_awards())
