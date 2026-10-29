# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Lint a Quarto deck source before rendering. Thresholds come from the CAS 2026 design contract.

  check_deck.py slides.qmd [--minutes 20]

HIGH blocks delivery, MEDIUM is a judgement call. Exit code 1 when any HIGH is found.
"""
import argparse, pathlib, re, sys
import yaml

WORDS = (70, 100)       # per slide: target, hard limit
ELEMENTS = (3, 4)       # bullets or boxes per slide
FRAGMENTS = (5, 6)
MIN_PER_SLIDE = 1.0     # minutes per content slide, below this the talk overruns
TABLE_ROWS = 7          # body rows of short cells; beyond this the table overflows in beamer and revealjs
TIMELINE = 14           # events on one .timeline axis
CELL_WORDS = 10
LEFTOVER = re.compile(r"\[(?:PLACEHOLDER|TODO|TBD|DATE[_A-Z]*|VENUE)[^\]]*\]|\bXXX\b|\bTODO\b|Author/Event|Date / Name of the event", re.I)
UNVERIFIED = re.compile(r"\[UNVERIFIED\]")

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("qmd", type=pathlib.Path)
ap.add_argument("--minutes", type=float, help="talk slot; default: `duration` in the front matter")
a = ap.parse_args()

text = a.qmd.read_text()
m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
fm, body = (yaml.safe_load(m.group(1)) or {}, text[m.end():]) if m else ({}, text)
findings = []  # (level, where, message)

for key in ("title", "author", "footer"):
    if not fm.get(key):
        findings.append(("HIGH", "front matter", f"`{key}` missing: the footer and title slide stay at template defaults"))


def prose(s):
    s = re.sub(r"```.*?```", "", s, flags=re.S)
    s = re.sub(r"^:{3,}\s*\{?\.?notes\}?.*?^:{3,}\s*$", "", s, flags=re.S | re.M)
    s = re.sub(r"^:{2,}.*$|<[^>]+>|!\[[^\]]*\]\([^)]*\)|\$[^$]+\$|`[^`]+`|https?://\S+|^\|.*\|$", " ", s, flags=re.M)
    return re.sub(r"[*_#>\-]", " ", s)


heads = list(re.finditer(r"^(#{1,2})\s+(.+)$", body, re.M))
content = 0
for i, h in enumerate(heads):
    level, title = h.group(1), h.group(2).strip()
    raw = body[h.end():heads[i + 1].start() if i + 1 < len(heads) else len(body)]
    where = f"{level} {title[:50]}"
    for hit in LEFTOVER.findall(title + raw):
        findings.append(("HIGH", where, f"leftover placeholder {hit!r}"))
    for _ in UNVERIFIED.findall(raw):
        findings.append(("HIGH", where, "[UNVERIFIED] claim on a slide: verify it or cut it"))
    for path in re.findall(r"!\[[^\]]*\]\(([^)\s]+)", raw):
        if not re.match(r"https?://", path) and not (a.qmd.parent / path).exists():
            findings.append(("HIGH", where, f"figure not found: {path}"))
    if level == "#" or ".plain" in title:
        continue
    content += 1
    words = len(prose(raw).split())
    # a .timeline list is one element; its events are checked against TIMELINE
    tl = re.search(r"^:{3,}\s*\{\.timeline[^}]*\}\s*$(.*?)^:{3,}\s*$", raw, re.S | re.M)
    if tl:
        events = len(re.findall(r"^\s*[-*+]\s+\S", tl.group(1), re.M))
        if events > TIMELINE:
            findings.append(("HIGH", where, f"timeline with {events} events (max {TIMELINE})"))
    flat = raw.replace(tl.group(1), "") if tl else raw
    items = len(re.findall(r"^\s*(?:[-*+]|\d+\.)\s+\S", flat, re.M)) + len(re.findall(r"^:{3,}\s*\{\.(?:callout|box|highlight|tile|card|step)\b", flat, re.M))
    frags = len(re.findall(r"\.fragment|\. \. \.|^\.\.\.$", raw, re.M))
    for value, (target, limit), what in ((words, WORDS, "words"), (items, ELEMENTS, "elements"), (frags, FRAGMENTS, "fragments")):
        if value > limit:
            findings.append(("HIGH", where, f"{value} {what} (limit {limit})"))
        elif value > target:
            findings.append(("MEDIUM", where, f"{value} {what} (target {target})"))
    rows = [r for r in re.findall(r"^\|(.*)\|\s*$", raw, re.M) if not re.fullmatch(r"[\s|:-]+", r)]
    if rows:
        cols = rows[0].count("|") + 1
        cell = max(len(c.split()) for r in rows for c in r.split("|"))
        if cols > 4:
            findings.append(("HIGH", where, f"table with {cols} columns (max 4)"))
        if len(rows) - 1 > TABLE_ROWS:
            findings.append(("HIGH", where, f"table with {len(rows) - 1} rows (max {TABLE_ROWS})"))
        if cell > CELL_WORDS:
            findings.append(("MEDIUM", where, f"table cell with {cell} words (target {CELL_WORDS})"))
        after = raw[raw.rfind("|") + 1:]
        after = re.sub(r"^:{3,}\s*\{\.notes\}.*", "", after, flags=re.S | re.M)
        if prose(after).split() or re.search(r"^\s*[-*+]\s", raw[:raw.find("|")], re.M):
            findings.append(("HIGH", where, "table shares the slide with other text: pptx splits it onto a second slide"))
    if words > WORDS[0] and not re.search(r"!\[|\{python\}|<iframe|\.svg|\.png", raw):
        findings.append(("MEDIUM", where, "dense slide with no figure"))

minutes = a.minutes or fm.get("duration")
if minutes and content > minutes / MIN_PER_SLIDE:
    findings.append(("HIGH", "deck", f"{content} content slides for {minutes:g} min (max {int(minutes / MIN_PER_SLIDE)})"))

for level, where, msg in sorted(findings, key=lambda f: f[0] != "HIGH"):
    print(f"{level:6} {where}: {msg}")
print(f"{content} content slides, {sum(f[0] == 'HIGH' for f in findings)} HIGH, {sum(f[0] == 'MEDIUM' for f in findings)} MEDIUM")
sys.exit(1 if any(f[0] == "HIGH" for f in findings) else 0)
