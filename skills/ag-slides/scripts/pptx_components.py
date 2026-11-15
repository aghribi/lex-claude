# /// script
# requires-python = ">=3.10"
# dependencies = ["python-pptx>=1.0", "pyyaml>=6"]
# ///
"""Quarto post-render step: draw tiles, cards, steps and diagrams in the deck's pptx as PowerPoint shapes.

  pptx_components.py [deck_dir]        default: the current directory (Quarto runs it from the project)

pandoc cannot draw them, so charter.lua writes their content to `_components.json` and leaves a bullet list on
the slide. This step removes that list and draws the component in the template body box, in the charter colours
and the template fonts. It also adds the `eyebrow:` label, smaller author lines and the institute on the title
slide. `.diagram` steps and `.build` items become groups that appear on click; `.sync` points and figures and a `.takeaway` follow their clicks. Slides already drawn (shapes named `agc:`) are left alone, so a rerun changes nothing.
"""
import functools, json, math, os, pathlib, sys
import yaml
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.util import Pt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from charter import NS, load, logo_box, logo_shift  # noqa: E402
from diagram import ICONS, layers, needs_frame, palette, rasterise  # noqa: E402

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


def group(slide):
    g = slide.shapes.add_group_shape()
    g.name = TAG + "step"
    return g


def effect(kind, spid, ids, node):
    """One effect on one shape: "in" fades it in, "out" fades it out, "dim" takes it to 40 % opacity."""
    t = f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'
    c, d, e = (next(ids) for _ in range(3))
    vis = ('<p:set><p:cBhvr><p:cTn id="{}" dur="1" fill="hold"><p:stCondLst><p:cond delay="{}"/></p:stCondLst></p:cTn>' + t +
           '<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="{}"/></p:to></p:set>')
    if kind == "in":
        preset, body = ("10", "entr"), (vis.format(d, 0, "visible") +
                                         f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{e}" dur="400"/>{t}</p:cBhvr></p:animEffect>')
    elif kind == "out":
        preset, body = ("10", "exit"), (f'<p:animEffect transition="out" filter="fade"><p:cBhvr><p:cTn id="{e}" dur="400"/>{t}</p:cBhvr></p:animEffect>' +
                                         vis.format(d, 399, "hidden"))
    else:
        preset, body = ("9", "emph"), (
            f'<p:set><p:cBhvr><p:cTn id="{d}" dur="400" fill="hold"/>{t}<p:attrNameLst><p:attrName>style.opacity</p:attrName></p:attrNameLst></p:cBhvr>'
            '<p:to><p:strVal val="0.4"/></p:to></p:set>'
            f'<p:animEffect transition="out" filter="image" prLst="opacity: 0.4"><p:cBhvr rctx="IE"><p:cTn id="{e}" dur="400" fill="hold"/>{t}</p:cBhvr></p:animEffect>')
    return (f'<p:par><p:cTn id="{c}" presetID="{preset[0]}" presetClass="{preset[1]}" presetSubtype="0" fill="hold" nodeType="{node}">'
            f'<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>{body}</p:childTnLst></p:cTn></p:par>')


def timeline(slide, clicks):
    """Each click runs its list of (kind, shape) effects together; see `effect`."""
    ids = iter(range(3, 10 ** 6))
    out = []
    for effects in clicks:
        a, b = next(ids), next(ids)
        inner = "".join(effect(kind, sh.shape_id, ids, "clickEffect" if j == 0 else "withEffect") for j, (kind, sh) in enumerate(effects))
        out.append(f'<p:par><p:cTn id="{a}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
                   f'<p:par><p:cTn id="{b}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>{inner}'
                   "</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>")
    xml = ('<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
           '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>' + "".join(out) +
           '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
           '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
           "</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>")
    sld = slide._element
    for old in sld.findall("p:timing", NS):
        sld.remove(old)
    ext = sld.find("p:extLst", NS)
    el = parse_xml(xml)
    ext.addprevious(el) if ext is not None else sld.append(el)


def animate(slide, groups):
    """Each group fades in on its own click."""
    timeline(slide, [[("in", g)] for g in groups])


def draw_prim(g, p, ox, oy, fonts):
    x, y = p.get("x", 0) + ox, p.get("y", 0) + oy
    if p["p"] in ("rect", "oval"):
        kind = MSO_SHAPE.OVAL if p["p"] == "oval" else (MSO_SHAPE.ROUNDED_RECTANGLE if p.get("radius") else MSO_SHAPE.RECTANGLE)
        r = g.shapes.add_shape(kind, Pt(x), Pt(y), Pt(p["w"]), Pt(p["h"]))
        r.name = TAG + "box"
        r.shadow.inherit = False
        if p.get("fill"):
            r.fill.solid()
            r.fill.fore_color.rgb = RGBColor.from_string(p["fill"])
            if p.get("alpha") is not None:
                clr = r.fill._xPr.find(f"{{{NS['a']}}}solidFill")[0]
                clr.append(parse_xml(f'<a:alpha xmlns:a="{NS["a"]}" val="{round(p["alpha"] * 100000)}"/>'))
        else:
            r.fill.background()
        if p.get("line"):
            r.line.color.rgb = RGBColor.from_string(p["line"])
            r.line.width = Pt(0.75)
        else:
            r.line.fill.background()
        if p.get("radius"):
            r.adjustments[0] = min(0.5, p["radius"] / min(p["w"], p["h"]))
    elif p["p"] in ("poly", "shape"):
        closed = p["p"] == "shape"
        pts = [(round((a + ox) * 100), round((b + oy) * 100)) for a, b in p["points"]]
        fb = g.shapes.build_freeform(pts[0][0], pts[0][1], scale=127)
        fb.add_line_segments(pts[1:], close=closed)
        r = fb.convert_to_shape()
        r.name = TAG + "line"
        r.shadow.inherit = False
        if closed:
            r.fill.solid()
            r.fill.fore_color.rgb = RGBColor.from_string(p["fill"])
            r.line.fill.background()
        else:
            r.fill.background()
            r.line.color.rgb = RGBColor.from_string(p["color"])
            r.line.width = Pt(p["width"])
            if p["dash"]:
                r.line.dash_style = MSO_LINE.DASH
    elif p["p"] == "image":
        pic = g.shapes.add_picture(str(p["path"]), Pt(x), Pt(y), Pt(p["w"]), Pt(p["h"]))
        pic.name = TAG + "image"
    else:
        tb = g.shapes.add_textbox(Pt(x), Pt(y), Pt(p["w"]), Pt(p["h"]))
        tb.name = TAG + "text"
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[p["anchor"]]
        for k in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, k, 0)
        for i, q in enumerate(p["paras"]):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[p["align"]]
            run = para.add_run()
            run.text = q["s"]
            run.font.size, run.font.bold, run.font.name = Pt(q["size"]), q.get("bold", False), fonts["head" if q.get("head") else "base"]
            run.font.color.rgb = RGBColor.from_string(q["color"])


def draw_diagram(slide, comp, body, col, fonts, ddir, slide_w):
    split_body(slide, body)
    spec = yaml.safe_load((ddir / comp["src"]).read_text())
    ox, oy = (slide_w - spec["size"][0]) / 2, body["y"] + 2
    groups = []
    for ps in layers(spec, col, ddir):
        g = group(slide)
        for p in ps:
            draw_prim(g, p, ox, oy, fonts)
        groups.append(g)
    animate(slide, groups[1:])


def draw(slide, comp, body, col, fonts, ddir):
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
    groups = []
    for i, it in enumerate(items):
        x = body["x"] + i * (w + gap)
        if comp.get("build"):
            groups.append(group(slide))
            pa = Painter(groups[-1], col, fonts)
        if kind == "tiles":
            h = 118
            y = bottom - h
            pa.rect(x, y, w, h, tint)
            pa.rect(x, y, 5, h, col["secondary"])
            pa.text(x + 18, y + 12, w - 26, 50, it["head"], 40, col["primary"], head=True, bold=True)
            pa.text(x + 18, y + 64, w - 26, h - 70, it["body"], 13, muted)
            continue
        y = top + (12 if kind == "steps" else 0)
        h = min(235 if it.get("icon") else 175, bottom - y)
        accent = col["secondary"] if it.get("accent") else col["primary"]
        pa.rect(x, y, w, h, "FFFFFF", line=line)
        pa.rect(x, y, w, 3, accent)
        ty = y + (20 if kind == "steps" else 14)
        if it.get("icon"):
            png = rasterise(ddir, f"{ICONS}/{it['icon']}.svg", color=col["primary"], px=192)
            pa.s.shapes.add_picture(str(png), Pt(x + 14), Pt(ty), Pt(30), Pt(30)).name = TAG + "icon"
            ty += 38
        hs = 16 if it.get("icon") else 19
        head_h = max(1, math.ceil(len(it["head"]) * 0.5 * hs / (w - 28))) * hs * 1.2
        pa.text(x + 14, ty, w - 28, head_h, it["head"], hs, col["primary"], head=True, bold=True)
        ty += head_h + 7
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
        pa.text(x + 14, ty, w - 28, y + h - ty - 10, it["body"], 15 if it.get("icon") else 13, muted)
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
    if groups:
        animate(slide, groups)


def rich(pa, x, y, w, h, parts, size, color, bold_color):
    """Text box from runs ({t, b}): bold runs in `bold_color`."""
    tb = pa.text(x, y, w, h, "", size, color)
    p = tb.text_frame.paragraphs[0]
    p._p.remove(p.runs[0]._r)
    for part in parts:
        r = p.add_run()
        r.text, r.font.size, r.font.name = part["t"], Pt(size), pa.fonts["base"]
        r.font.bold = bool(part.get("b"))
        r.font.color.rgb = RGBColor.from_string(bold_color if part.get("b") else color)
    return tb


def lines(parts, size, w):
    return max(1, math.ceil(sum(len(p["t"]) for p in parts) * 0.5 * size / w))


def draw_takeaway(slide, comp, body, col, fonts):
    """The message box at the bottom of the body; returns it as a group, to animate."""
    g = group(slide)
    pa = Painter(g, col, fonts)
    h = lines(comp["runs"], 16, body["w"] - 30) * 16 * 1.25 + 14
    y = body["y"] + body["h"] - h
    pa.rect(body["x"], y, body["w"], h, mix(col["secondary"], "FFFFFF", 0.14))
    pa.rect(body["x"], y, 5, h, col["secondary"])
    t = rich(pa, body["x"] + 18, y, body["w"] - 30, h, comp["runs"], 16, col["primary"], col["primary"])
    t.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    for r in t.text_frame.paragraphs[0].runs:
        r.font.bold = True
    return g, h


def draw_spotlight(slide, comp, size, col, fonts):
    """The `.spotlight` card over a white veil, as one group: label strip, then one paragraph per block."""
    g = group(slide)
    g.name = TAG + "spotlight"
    pa = Painter(g, col, fonts)
    sw, sh = size
    veil = pa.rect(0, 0, sw, sh, "FFFFFF")
    clr = veil.fill._xPr.find(f"{{{NS['a']}}}solidFill")[0]
    clr.append(parse_xml(f'<a:alpha xmlns:a="{NS["a"]}" val="86000"/>'))
    w = sw * 0.6
    body = [lines(par, 18, w - 40) * 18 * 1.3 + 8 for par in comp["paras"]]
    h = 34 + sum(body) + 24
    x, y = (sw - w) / 2, (sh - h) / 2
    pa.rect(x, y, w, h, "FFFFFF", line=col["primary"], kind=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
    pa.rect(x + 2, y + 2, w - 4, 30, col["primary"])
    pa.text(x + 20, y + 2, w - 40, 30, comp["label"], 11, "FFFFFF", bold=True, upper=True, anchor=MSO_ANCHOR.MIDDLE, spacing=80)
    ty = y + 46
    for par, bh in zip(comp["paras"], body):
        rich(pa, x + 20, ty, w - 40, bh, par, 18, col["ink"], col["primary"])
        ty += bh
    return g


def append_click(slide, g):
    """`g` fades in on one more click, after the slide's existing ones."""
    seq = slide._element.find(".//p:seq/p:cTn/p:childTnLst", NS)
    if seq is None:
        animate(slide, [g])
        return
    ids = iter(range(max(int(c.get("id")) for c in slide._element.iter(f"{{{NS['p']}}}cTn")) + 1, 10 ** 6))
    a, b = next(ids), next(ids)
    seq.append(parse_xml(f'<p:par xmlns:p="{NS["p"]}"><p:cTn id="{a}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
                         f'<p:childTnLst><p:par><p:cTn id="{b}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                         + effect("in", g.shape_id, ids, "clickEffect") + "</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>"))


def draw_sync(slide, comp, body, col, fonts, ddir, take=None, spot=None):
    """Points left, figures right; each click shows a point and its figure, the previous point dims.

    `spot`: a function drawing the `.spotlight` that follows point
    comp["spot"]; it takes the click before the next point.
    """
    from PIL import Image
    split_body(slide, body)
    clicks, bottom = [], body["y"] + body["h"]
    if take:
        tg, th = draw_takeaway(slide, take, body, col, fonts)
        bottom -= th + 10
    lw = body["w"] * 0.42
    rx, rw = body["x"] + lw + 20, body["w"] - lw - 20
    size, items = 16, comp["items"]
    hs = [lines(it["runs"], size, lw - 16) * size * 1.25 for it in items]
    gap = 14
    leg_h = 110  # a legend sits under its point, over the room of the points still to come
    y = body["y"] + max(0, (bottom - body["y"] - sum(hs) - gap * (len(hs) - 1)) / 2)
    points, figs = [], []  # figs[k]: the figure group shown with point k (a point without fig keeps the last one)
    for it, h in zip(items, hs):
        g = group(slide)
        pa = Painter(g, col, fonts)
        if it.get("icon"):
            png = rasterise(ddir, f"{ICONS}/{it['icon']}.svg", color=col["secondary"], px=192)
            pa.s.shapes.add_picture(str(png), Pt(body["x"]), Pt(y + 1), Pt(size), Pt(size)).name = TAG + "icon"
        else:
            pa.rect(body["x"], y + size * 0.45, 6, 6, col["secondary"], kind=MSO_SHAPE.OVAL)
        indent = size + 8 if it.get("icon") else 16
        rich(pa, body["x"] + indent, y, lw - indent, h, it["runs"], size, col["foreground"], col["primary"])
        points.append(g)
        it["bottom"] = y + h
        y += h + gap
        if not it.get("fig"):
            figs.append(figs[-1])
            continue
        g = group(slide)
        credit_h = 14 if it.get("credit") else 0
        with Image.open(ddir / it["fig"]) as im:
            iw, ih = im.size
        avail = bottom - body["y"] - credit_h
        scale = min(rw / iw, avail / ih)
        w, h_img = iw * scale, ih * scale
        fy = body["y"] + (avail - h_img) / 2
        pic = g.shapes.add_picture(str(ddir / it["fig"]), Pt(rx + (rw - w) / 2), Pt(fy), Pt(w), Pt(h_img))
        pic.name = TAG + "fig"
        if needs_frame(ddir / it["fig"], col["paper"]):
            pic.line.color.rgb = RGBColor.from_string(mix(col["foreground"], "FFFFFF", 0.25))
            pic.line.width = Pt(0.75)
        if credit_h:
            Painter(g, col, fonts).text(rx, fy + h_img + 2, rw, 12, it["credit"], 9, mix(col["foreground"], "FFFFFF", 0.6), align=PP_ALIGN.CENTER)
        figs.append(g)
    for it, g in zip(items, figs):
        if it.get("fig") and it.get("legend"):
            with Image.open(ddir / it["legend"]) as im:
                iw, ih = im.size
            scale = min(lw * 0.85 / iw, leg_h / ih)  # centred under its own point
            lx = body["x"] + (lw - iw * scale) / 2
            pic = g.shapes.add_picture(str(ddir / it["legend"]), Pt(lx), Pt(it["bottom"] + 8), Pt(iw * scale), Pt(ih * scale))
            pic.name = TAG + "legend"
    sg = spot() if spot else None
    for k in range(1, len(items)):
        swap = [("out", figs[k - 1]), ("in", figs[k])] if figs[k] is not figs[k - 1] else []
        leave = []
        if sg is not None and k == comp["spot"]:
            clicks.append([("in", sg)])
            leave = [("out", sg)]
        clicks.append([("in", points[k]), ("dim", points[k - 1])] + swap + leave)
    if take:
        clicks.append([("in", tg), ("dim", points[-1])])
    timeline(slide, clicks)


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


def place_logo(slide, src, box, shift):
    """Logo left-aligned and centred in `box`, aspect kept; the title moves right by `shift`."""
    pic = slide.shapes.add_picture(str(src), 0, 0, height=Pt(box["h"]))
    if pic.width > Pt(box["w"]):
        pic.height = int(pic.height * Pt(box["w"]) / pic.width)
        pic.width = Pt(box["w"])
    pic.left = Pt(box["x"])
    if slide.shapes.title is not None:
        slide.shapes.title.left += Pt(shift)
        slide.shapes.title.width -= Pt(shift)
    pic.top = Pt(box["y"] + box["h"] / 2) - pic.height // 2
    pic.name = TAG + "logo"


def template_fonts(prs):
    m = prs.slide_masters[0]._element
    def face(style):
        return (m.find(f".//p:txStyles/p:{style}//a:latin", NS).get("typeface"))
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
    col = palette(brand)
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
        comps = [c for c in data["slides"] if c["title"] == title]
        sync = next((c for c in comps if c["kind"] == "sync"), None)
        take = next((c for c in comps if c["kind"] == "takeaway"), None)
        size = (prs.slide_width / 12700, prs.slide_height / 12700)
        inner = next((c for c in comps if c["kind"] == "spotlight" and c.get("after") is not None), None)
        for comp in comps:
            if comp["kind"] == "logo":
                place_logo(slide, ddir / comp["src"], logo_box(geo), logo_shift(geo))
                continue
            if comp["kind"] == "sync":
                spot = inner and functools.partial(draw_spotlight, slide, inner, size, col, fonts)
                draw_sync(slide, comp, body, col, fonts, ddir, take, spot)
            elif comp["kind"] == "takeaway":
                if sync is None:  # alone it comes on a click; next to a diagram or cards it stays put
                    split_body(slide, body)
                    g = draw_takeaway(slide, comp, body, col, fonts)[0]
                    if all(c["kind"] in ("logo", "takeaway") for c in comps):
                        animate(slide, [g])
                continue
            elif comp["kind"] == "spotlight":
                continue  # drawn last, over everything else on the slide
            elif comp["kind"] == "diagram":
                draw_diagram(slide, comp, body, col, fonts, ddir, prs.slide_width / 12700)
            else:
                draw(slide, comp, body, col, fonts, ddir)
            drawn += 1
        for comp in (c for c in comps if c["kind"] == "spotlight" and c.get("after") is None):
            for ph in slide.placeholders:  # its fallback line only: the slide's own bullets stay
                for par in list(ph.text_frame.paragraphs) if ph.has_text_frame else []:
                    if par.text.strip() == "spotlight":
                        par._p.getparent().remove(par._p)
            append_click(slide, draw_spotlight(slide, comp, size, col, fonts))
            drawn += 1
    prs.save(pptx)
    print(f"pptx_components: {drawn} components drawn in {pptx}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
