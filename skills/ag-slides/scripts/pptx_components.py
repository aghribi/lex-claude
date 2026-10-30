# /// script
# requires-python = ">=3.10"
# dependencies = ["python-pptx>=1.0", "pyyaml>=6"]
# ///
"""Quarto post-render step: draw tiles, cards and steps in the deck's pptx as PowerPoint shapes.

  pptx_components.py [deck_dir]        default: the current directory (Quarto runs it from the project)

pandoc cannot draw them, so charter.lua writes their content to `_components.json` and leaves a bullet list on
the slide. This step removes that list and draws the component in the template body box, in the charter colours
and the template fonts. It also adds the `eyebrow:` label, smaller author lines and the institute on the title
slide. Slides already drawn (shapes named `agc:`) are left alone, so a rerun changes nothing.
"""
import json, math, os, pathlib, sys
import yaml
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Pt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from charter import NS, colors, load  # noqa: E402

TAG = "agc:"


def mix(a, b, w):
    """w of colour a over colour b, hex strings without #."""
    return "".join(f"{round(int(a[i:i + 2], 16) * w + int(b[i:i + 2], 16) * (1 - w)):02X}" for i in (0, 2, 4))


class Painter:
    def __init__(self, slide, col, fonts):
        self.s, self.col, self.fonts = slide, col, fonts

    def rect(self, x, y, w, h, fill, line=None, kind=MSO_SHAPE.RECTANGLE, radius=None):
        r = self.s.shapes.add_shape(kind, Pt(x), Pt(y), Pt(w), Pt(h))
        r.name = TAG + "box"
        r.shadow.inherit = False
        r.fill.solid()
        r.fill.fore_color.rgb = RGBColor.from_string(fill)
        if line:
            r.line.color.rgb = RGBColor.from_string(line)
            r.line.width = Pt(0.75)
        else:
            r.line.fill.background()
        if radius is not None:
            r.adjustments[0] = radius
        return r

    def text(self, x, y, w, h, s, size, color, head=False, bold=False, align=None, anchor=MSO_ANCHOR.TOP, upper=False, spacing=None):
        tb = self.s.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
        tb.name = TAG + "text"
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        for k in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, k, 0)
        p = tf.paragraphs[0]
        if align:
            p.alignment = align
        run = p.add_run()
        run.text = s.upper() if upper else s
        f = run.font
        f.size, f.bold = Pt(size), bold
        f.name = self.fonts["head" if head else "base"]
        f.color.rgb = RGBColor.from_string(color)
        if spacing:
            run._r.get_or_add_rPr().set("spc", str(spacing))
        return tb


def split_body(slide, body):
    """Drop the fallback list from the body placeholder. Text before it stays as the lead (its height in pt is
    returned); text after it (a source credit) is removed and returned, to be set small under the component."""
    ph = next((p for p in slide.placeholders if p.placeholder_format.idx == 1), None)
    if ph is None:
        return 0, ""
    lead, after, seen_list = [], [], False
    for p in list(ph.text_frame.paragraphs):
        ppr = p._p.find("a:pPr", NS)
        plain = ppr is not None and ppr.find("a:buNone", NS) is not None
        if plain and not seen_list:
            lead.append(p)
            continue
        seen_list = seen_list or not plain
        if plain:
            after.append(p.text)
        p._p.getparent().remove(p._p)
    text = " ".join(p.text for p in lead).strip()
    if not text:
        ph._element.getparent().remove(ph._element)
        return 0, " ".join(after).strip()
    size = 22
    for p in lead:  # the lead reads as one block at a fixed size
        for r in p.runs:
            r.font.size = Pt(size)
    lines = max(1, math.ceil(len(text) * 0.5 * size / body["w"]))
    h = lines * size * 1.25 + 8
    # a placeholder that inherits its box gets a fresh xfrm: set all four sides, or its width is 0
    ph.left, ph.top, ph.width, ph.height = Pt(body["x"]), Pt(body["y"]), Pt(body["w"]), Pt(h)
    return h, " ".join(after).strip()


def draw(slide, comp, body, col, fonts):
    pa = Painter(slide, col, fonts)
    items, kind = comp["items"], comp["kind"]
    lead_h, note = split_body(slide, body)
    top = body["y"] + lead_h + 14
    bottom = body["y"] + body["h"]
    if note:
        bottom -= 16
        pa.text(body["x"], bottom + 4, body["w"], 12, note, 9, mix(col["primary"], "FFFFFF", 0.6), align=PP_ALIGN.RIGHT)
    n = len(items)
    gap = 22 if kind == "steps" else 14
    w = (body["w"] - gap * (n - 1)) / n
    tint, line, muted = mix(col["secondary"], "FFFFFF", 0.14), mix(col["primary"], "FFFFFF", 0.25), mix(col["foreground"], "FFFFFF", 0.78)
    for i, it in enumerate(items):
        x = body["x"] + i * (w + gap)
        if kind == "tiles":
            h = 118
            y = bottom - h
            pa.rect(x, y, w, h, tint)
            pa.rect(x, y, 5, h, col["secondary"])
            pa.text(x + 18, y + 12, w - 26, 50, it["head"], 40, col["primary"], head=True, bold=True)
            pa.text(x + 18, y + 64, w - 26, h - 70, it["body"], 13, muted)
            continue
        y = top + (12 if kind == "steps" else 0)
        h = min(175, bottom - y)
        accent = col["secondary"] if it.get("accent") else col["primary"]
        pa.rect(x, y, w, h, "FFFFFF", line=line)
        pa.rect(x, y, w, 3, accent)
        ty = y + (20 if kind == "steps" else 14)
        pa.text(x + 14, ty, w - 28, 26, it["head"], 19, col["primary"], head=True, bold=True)
        ty += 30
        if it.get("tag"):
            tw = 0.62 * 9 * len(it["tag"]) + 12
            pill = pa.rect(x + 14, ty, tw, 15, col["secondary"], kind=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.3)
            tf = pill.text_frame
            for k in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
                setattr(tf, k, 0)
            tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            r = tf.paragraphs[0].add_run()
            r.text, r.font.size, r.font.bold, r.font.name = it["tag"], Pt(9), True, fonts["base"]
            r.font.color.rgb = RGBColor.from_string("FFFFFF")
            ty += 21
        pa.text(x + 14, ty, w - 28, y + h - ty - 10, it["body"], 13, muted)
        if kind == "steps":
            dot = pa.rect(x + 12, y - 11, 22, 22, col["secondary"], kind=MSO_SHAPE.OVAL)
            tf = dot.text_frame
            for k in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
                setattr(tf, k, 0)
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            r = tf.paragraphs[0].add_run()
            r.text, r.font.size, r.font.bold, r.font.name = str(i + 1), Pt(11), True, fonts["base"]
            r.font.color.rgb = RGBColor.from_string("FFFFFF")
            if i < n - 1:
                arrow = pa.rect(x + w + 6, y + h / 2 - 6, 10, 12, col["secondary"], kind=MSO_SHAPE.ISOSCELES_TRIANGLE)
                arrow.rotation = 90


def title_slide(slide, data, geo, col, fonts):
    ph = next((p for p in slide.placeholders if p.placeholder_format.idx == 1), None)
    if ph is not None:
        paras = ph.text_frame.paragraphs
        for p in paras[1:]:  # author lines under the subtitle
            for r in p.runs:
                r.font.size = Pt(16)
        if data.get("institute") and all(p.text.strip() != data["institute"] for p in paras):
            p = ph.text_frame.add_paragraph()
            r = p.add_run()
            r.text, r.font.size = data["institute"], Pt(16)
    if data.get("eyebrow"):
        t = geo["title"]["title"]
        size = t.get("size", 54)
        y = t["y"] + t["h"] - 3.6 - size * 1.15 - 24
        Painter(slide, col, fonts).text(t["x"] + 7.2, y, t["w"], 18, data["eyebrow"], 12, mix(col["secondary"], "FFFFFF", 0.75), bold=True, upper=True, spacing=200)


def template_fonts(prs):
    m = prs.slide_masters[0]._element
    face = lambda style: (m.find(f".//p:txStyles/p:{style}//a:latin", NS).get("typeface"))
    return {"head": face("titleStyle"), "base": face("bodyStyle")}


def main(ddir):
    data_file, pptx = ddir / "_components.json", ddir / "build" / "slides.pptx"
    outputs = os.environ.get("QUARTO_PROJECT_OUTPUT_FILES")
    if not data_file.exists() or not pptx.exists() or (outputs is not None and "slides.pptx" not in outputs):
        return
    proj = yaml.safe_load((ddir / "_quarto.yml").read_text()) or {}
    cdir = pathlib.Path(proj["charter"])
    cfg, brand = load(cdir)
    geo = yaml.safe_load((cdir / "build" / "geometry.yml").read_text())
    col = colors(brand)
    data = json.loads(data_file.read_text())
    prs = Presentation(pptx)
    fonts = template_fonts(prs)
    body = geo["content"]["body"]
    drawn = 0
    for i, slide in enumerate(prs.slides):
        if any(sh.name.startswith(TAG) for sh in slide.shapes):
            continue
        if i == 0:
            title_slide(slide, data, geo, col, fonts)
            continue
        title = slide.shapes.title.text_frame.text.strip() if slide.shapes.title is not None else ""
        for comp in (c for c in data["slides"] if c["title"] == title):
            draw(slide, comp, body, col, fonts)
            drawn += 1
    prs.save(pptx)
    print(f"pptx_components: {drawn} components drawn in {pptx}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
