# /// script
# requires-python = ">=3.10"
# dependencies = ["python-pptx>=1.0", "pyyaml>=6"]
# ///
"""Quarto post-render step: draw the links.yml strip in the deck's pptx, between body and footer.

  pptx_links.py [deck_dir]        default: the current directory (Quarto runs it from the project)

Slides already drawn (shapes named `agl:`) are left alone, so a rerun changes nothing.
"""
import json, pathlib, sys
import yaml
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml import parse_xml
from pptx.util import Pt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from charter import NS, colors, load, strip_bottom  # noqa: E402
from pptx_components import effect  # noqa: E402

TAG = "agl:"
ROW, ICON, SIZE = 14, 11, 9.5  # pt
CHAR_W = 4.9  # pt per character at SIZE, to lay out the row


def draw_link(shapes, it, x, y, w, col, icons):
    kind, label, url = it[:3]
    if kind != "ref":
        pic = shapes.add_picture(str(icons / f"{kind}.png"), Pt(x), Pt(y + 1), Pt(ICON), Pt(ICON))
        pic.name = TAG + "icon"
        x += ICON + 2
        w -= ICON + 2
    tb = shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(ROW))
    tb.name = TAG + "link"
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    run = tf.paragraphs[0].add_run()
    run.text = label
    run.font.size = Pt(SIZE)
    run.font.italic = kind == "ref"
    run.font.color.rgb = RGBColor.from_string(col["foreground" if kind == "ref" else "secondary"])
    run.hyperlink.address = url


def width(it):
    return len(it[1]) * CHAR_W + 8 + (0 if it[0] == "ref" else ICON + 2)


def strip(slide, items, box, bottom, col, icons, points, spot=None):
    """Icon and hyperlinked label in rows that grow upwards from the footer. Links with a fourth field n
    (the n-th point of the slide's `.sync`) share one cell after the others and swap with their point."""
    always = [it for it in items if len(it) < 4]
    steps = {}
    for it in items:
        if len(it) > 3:
            steps.setdefault(int(it[3]), []).append(it)
    rows = [[]]
    x = 0
    for it in always:
        w = width(it)
        if rows[-1] and x + w > box["w"]:
            rows.append([])
            x = 0
        rows[-1].append((it, x, w))
        x += w + 8
    for r, row in enumerate(rows):
        y = bottom - ROW * (len(rows) - r)
        for it, lx, w in row:
            draw_link(slide.shapes, it, box["x"] + lx, y, w, col, icons)
    if not steps:
        return
    y = bottom - ROW
    groups = {}
    for s, its in steps.items():
        g = slide.shapes.add_group_shape()
        g.name = TAG + "step"
        sx = x
        for it in its:
            draw_link(g.shapes, it, box["x"] + sx, y, width(it), col, icons)
            sx += width(it) + 8
        groups[s] = g
    add_to_clicks(slide, groups, points, spot)


def spotlight_on_top(slide):
    """The `.spotlight` veil covers the strip too."""
    ext = slide.shapes._spTree.find("p:extLst", NS)
    for sh in [sh for sh in slide.shapes if sh.name == "agc:spotlight"]:
        if ext is not None:
            ext.addprevious(sh._element)
        else:
            slide.shapes._spTree.append(sh._element)


def add_to_clicks(slide, groups, points, spot=None):
    """Point p shows on click p - 1 (pptx_components.py); the links of point s come in with it and leave with
    point s + 1. A spotlight after point `spot` takes one more click there."""
    seq = slide._element.find(".//p:seq/p:cTn/p:childTnLst", NS)
    if seq is None:
        return
    clicks = seq.findall("p:par", NS)
    ids = iter(range(max(int(c.get("id")) for c in slide._element.iter("{%s}cTn" % NS["p"])) + 1, 10 ** 6))

    def at(p):
        return p - 2 + (1 if spot is not None and p > spot else 0)

    for s, g in groups.items():
        for kind, click in (("in", at(s)), ("out", at(s + 1))):
            if click < 0 or click >= len(clicks) or (kind == "out" and s >= points):
                continue
            inner = clicks[click].find("p:cTn/p:childTnLst/p:par/p:cTn/p:childTnLst", NS)
            inner.append(parse_xml(f'<p:root xmlns:p="{NS["p"]}">' + effect(kind, g.shape_id, ids, "withEffect") + "</p:root>")[0])


def expand(items, talks):
    """[talk, url, n] -> [talk, label, url, n], label from _talks.json (talks.py)."""
    out = []
    for it in items:
        if it[0] == "talk":
            if it[1] not in talks:
                sys.exit(f"pptx_links.py: talk {it[1]} missing from _talks.json; is talks.py in the pre-render hook?")
            out.append(["talk", talks[it[1]]["label"], it[1], *it[2:3]])
        else:
            out.append(it)
    return out


def main(ddir):
    src, pptx = ddir / "links.yml", ddir / "build" / "slides.pptx"
    if not src.exists() or not pptx.exists():
        return
    cache = ddir / "_talks.json"
    talks = json.loads(cache.read_text()) if cache.exists() else {}
    links = {k.replace("’", "'"): expand(v, talks) for k, v in yaml.safe_load(src.read_text()).items()}
    cdir = pathlib.Path((yaml.safe_load((ddir / "_quarto.yml").read_text()) or {})["charter"])
    cfg, brand = load(cdir)
    geo = yaml.safe_load((cdir / "build" / "geometry.yml").read_text())
    icons = ddir / "_extensions" / cfg["name"] / "icons"
    comps = ddir / "_components.json"
    points = {c["title"].replace("’", "'"): (len(c["items"]), c.get("spot"))
              for c in json.loads(comps.read_text())["slides"]
              if c["kind"] == "sync"} if comps.exists() else {}
    prs = Presentation(pptx)
    for slide in prs.slides:
        title = slide.shapes.title.text.replace("’", "'") if slide.shapes.title else ""
        if title in links and not any(s.name.startswith(TAG) for s in slide.shapes):
            strip(slide, links[title], geo["content"]["body"], strip_bottom(geo), colors(brand), icons,
                  *points.get(title, (0, None)))
            spotlight_on_top(slide)
    prs.save(pptx)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
