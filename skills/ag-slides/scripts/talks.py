# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Quarto pre-render step: resolve the `talk` links of links.yml from Indico.

  talks.py [deck_dir]        default: the current directory (Quarto runs it from the project)

A talk at the same event is written in links.yml as `[talk, <contribution URL>]`, with an optional third field n
that ties it to the n-th `.sync` point, like the fourth field of the other kinds. Speaker, title, day, time and room
come from the event's public export (`/export/event/<id>.json?detail=contributions`), fetched once per event.

Writes `_talks.json` (contribution URL -> label, title, start, room), read by links.lua and pptx_links.py, and
`_talks.qmd`, a "Related talks here" slide listing every linked talk in time order, for the deck to include.
When Indico cannot be reached, the previous `_talks.json` is kept; with no cache at all the render stops.
"""
import datetime as dt, json, pathlib, re, sys, urllib.request
import yaml

CONTRIB = re.compile(r"(https?://[^/]+)/event/(\d+)/contributions/(\d+)")


def speaker(person):
    """'Kim, Keon Hee' -> 'K. H. Kim'."""
    last, _, first = person["fullName"].partition(", ")
    initials = " ".join(p[0] + "." for p in re.split(r"[\s-]+", first) if p)
    return f"{initials} {last.title() if last.isupper() else last}".strip()


def fetch(host, event):
    url = f"{host}/export/event/{event}.json?detail=contributions"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)["results"][0]["contributions"]


def resolve(urls):
    out = {}
    events = {}
    for u in urls:
        host, event, db = CONTRIB.match(u).groups()
        events.setdefault((host, event), {})[int(db)] = u
    for (host, event), wanted in events.items():
        for c in fetch(host, event):
            if c["db_id"] not in wanted:
                continue
            sd = c["startDate"]
            start = dt.datetime.fromisoformat(f"{sd['date']}T{sd['time']}")
            who = " and ".join(speaker(p) for p in c.get("speakers", [])) or "TBA"
            out[wanted[c["db_id"]]] = {"label": f"{who} · {start:%a %H:%M}", "speakers": who, "title": c["title"],
                                       "start": start.isoformat(), "room": c.get("roomFullname") or c.get("room") or ""}
    missing = set(urls) - set(out)
    if missing:
        sys.exit(f"talks.py: not found on Indico: {sorted(missing)}")
    return out


def slide(talks):
    rows = []
    for url, t in sorted(talks.items(), key=lambda kv: kv[1]["start"]):
        start = dt.datetime.fromisoformat(t["start"])
        room = f", {t['room']}" if t["room"] else ""
        rows.append(f"- **{start:%a %d %b, %H:%M}{room}.** {t['speakers']}: [{t['title']}]({url}){{target=\"_blank\"}}")
    # Beamer: the full titles at the default size run into the footer
    return ("## Related talks here {.nocontents}\n\n"
            "```{=latex}\n\\setbeamerfont{itemize/enumerate body}{size=\\small}\n```\n\n" + "\n".join(rows) + "\n")


def main(ddir):
    src = ddir / "links.yml"
    if not src.exists():
        return
    urls = sorted({str(it[1]) for items in (yaml.safe_load(src.read_text()) or {}).values() for it in items
                   if it and it[0] == "talk"})
    cache = ddir / "_talks.json"
    if not urls:
        cache.unlink(missing_ok=True)
        (ddir / "_talks.qmd").write_text("")
        return
    try:
        talks = resolve(urls)
    except OSError as e:
        if not cache.exists():
            sys.exit(f"talks.py: Indico unreachable and no _talks.json yet: {e}")
        print(f"talks.py: Indico unreachable ({e}), keeping _talks.json")
        talks = json.loads(cache.read_text())
    cache.write_text(json.dumps(talks, ensure_ascii=False, indent=1))
    (ddir / "_talks.qmd").write_text(slide(talks))


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
