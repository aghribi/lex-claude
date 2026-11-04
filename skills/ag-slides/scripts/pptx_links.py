# /// script
# requires-python = ">=3.10"
# dependencies = ["python-pptx>=1.0", "pyyaml>=6"]
# ///
"""Quarto post-render step: draw the links.yml strip in the deck's pptx, between body and footer.

  pptx_links.py [deck_dir]        default: the current directory (Quarto runs it from the project)

Slides already drawn (shapes named `agl:`) are left alone, so a rerun changes nothing.
"""
import pathlib, sys
import yaml
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Pt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from charter import colors, load, strip_bottom  # noqa: E402

TAG = "agl:"
ROW, ICON, SIZE = 14, 11, 9.5  # pt
CHAR_W = 4.9  # pt per character at SIZE, to lay out the row


def strip(slide, items, box, bottom, col, icons):
    """Icon and hyperlinked label in rows that grow upwards from the footer."""
    rows = [[]]
    x = 0
    for it in items:
        w = len(it[1]) * CHAR_W + 8 + (0 if it[0] == "ref" else ICON + 2)
        if rows[-1] and x + w > box["w"]:
            rows.append([])
            x = 0
        rows[-1].append((it, x, w))
        x += w + 8
    for r, row in enumerate(rows):
        y = bottom - ROW * (len(rows) - r)
        for (kind, label, url), x, w in row:
            x += box["x"]
            if kind != "ref":
                pic = slide.shapes.add_picture(str(icons / f"{kind}.png"), Pt(x), Pt(y + 1), Pt(ICON), Pt(ICON))
                pic.name = TAG + "icon"
                x += ICON + 2
                w -= ICON + 2
            tb = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(ROW))
            tb.name = TAG + "link"
            tf = tb.text_frame
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            run = tf.paragraphs[0].add_run()
            run.text = label
            run.font.size = Pt(SIZE)
            run.font.italic = kind == "ref"
            run.font.color.rgb = RGBColor.from_string(col["foreground" if kind == "ref" else "secondary"])
            run.hyperlink.address = url


def main(ddir):
    src, pptx = ddir / "links.yml", ddir / "build" / "slides.pptx"
    if not src.exists() or not pptx.exists():
        return
    links = {k.replace("’", "'"): v for k, v in yaml.safe_load(src.read_text()).items()}
    cdir = pathlib.Path((yaml.safe_load((ddir / "_quarto.yml").read_text()) or {})["charter"])
    cfg, brand = load(cdir)
    geo = yaml.safe_load((cdir / "build" / "geometry.yml").read_text())
    icons = ddir / "_extensions" / cfg["name"] / "icons"
    prs = Presentation(pptx)
    for slide in prs.slides:
        title = slide.shapes.title.text.replace("’", "'") if slide.shapes.title else ""
        if title in links and not any(s.name.startswith(TAG) for s in slide.shapes):
            strip(slide, links[title], geo["content"]["body"], strip_bottom(geo), colors(brand), icons)
    prs.save(pptx)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
