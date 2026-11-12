# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10", "python-pptx>=1.0", "pyyaml>=6"]
# ///
"""Quarto pre-render step: turn the deck's `.diagram` specs into drawings, and fetch the icons the deck names.

  diagram.py [deck_dir]        default: the current directory (Quarto runs it from the project)

A spec is a YAML file: `size: [w, h]` in pt and `steps:`, each with an optional `caption:` and a `draw:` list.
Steps stack: what a step draws stays until a later step paints over it, so a `clear:` or a full-canvas image
swaps the picture and a caption replaces the previous one. Elements:

  box: [x, y, w, h]   style: dark | blue | tint | paper | ghost; title:, sub:, size:, radius:
  flow: [[x, y], ...]  moving green wire with an arrow; line: [[x, y], ...] a plain one (arrow: true)
  text: "..."          at: [x, y], w:, h:, size:, color:, bold:, head:, align: l|c|r, anchor: t|m|b
  image: path          box: [x, y, w, h], fitted without distortion; svg files are rasterised. An animated gif plays in
                       revealjs and pptx; `poster: png` is what beamer shows
  icon: name           box: [x, y, w, h], color:; lucide icon
  dot: [x, y]          r:, color:, diamond: true
  clear: [x, y, w, h]  paints the slide background

Writes `_diagrams/<name>.svg` (revealjs, inline, steps as fragments), `_diagrams/<name>-<n>.pdf` (beamer, one per
step). pptx_components.py draws the same primitives as PowerPoint shapes. `prims()` is the one layout.
"""
import base64, io, math, pathlib, re, subprocess, sys, urllib.request
from html import escape
import yaml
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from charter import colors, font_stack, load  # noqa: E402

LUCIDE = "https://cdn.jsdelivr.net/npm/lucide-static@1.66.0/icons/{}.svg"
OUT, ICONS = "_diagrams", "_icons"
CAPTION_H = 40


def mix(a, b, w):
    """w of colour a over colour b, hex strings without #."""
    return "".join(f"{round(int(a[i:i + 2], 16) * w + int(b[i:i + 2], 16) * (1 - w)):02X}" for i in (0, 2, 4))


def palette(brand):
    c = colors(brand)
    return c | {"ink": c["foreground"], "paper": c["background"], "white": "FFFFFF", "tint": mix(c["secondary"], "FFFFFF", 0.14),
                "edge": mix(c["primary"], "FFFFFF", 0.25), "muted": mix(c["foreground"], "FFFFFF", 0.72)}


def rasterise(ddir, path, color=None, px=1024):
    """Path of a PNG for an image file; svg goes through rsvg-convert, `color` fills in an icon's currentColor."""
    src = ddir / path
    if src.suffix.lower() != ".svg":
        return src
    out = ddir / OUT / "png" / f"{src.stem}{'-' + color if color else ''}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        svg = src.read_bytes().replace(b"currentColor", b"#" + color.encode()) if color else src.read_bytes()
        subprocess.run(["rsvg-convert", "-w", str(px), "--keep-aspect-ratio", "-o", out], input=svg, check=True)
    return out


def fit(png, x, y, w, h):
    iw, ih = Image.open(png).size
    k = min(w / iw, h / ih)
    return x + (w - iw * k) / 2, y + (h - ih * k) / 2, iw * k, ih * k


def wrap(s, w, size, head=False):
    """Lines of s in a box w pt wide. Width estimate per face; PowerPoint wraps on its own, with its own metrics."""
    cpl = max(1, int(w / (size * (0.44 if head else 0.5))))
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > cpl:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur] if cur else lines


def arrow_head(points, size=9):
    (x0, y0), (x1, y1) = points[-2], points[-1]
    d = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    return [(x1, y1), (x1 - size * ux + size * 0.55 * uy, y1 - size * uy - size * 0.55 * ux), (x1 - size * ux - size * 0.55 * uy, y1 - size * uy + size * 0.55 * ux)]


def prims(el, spec_size, col, ddir):
    """One spec element as primitives: rect, poly, shape (filled polygon), para (text block), image."""
    if "box" in el and "image" not in el and "icon" not in el:
        x, y, w, h = el["box"]
        st = el.get("style", "paper")
        fill, line, fg, fg2 = {
            "dark": (col["ink"], None, "FFFFFF", mix("FFFFFF", col["ink"], 0.78)),
            "blue": (col["primary"], None, "FFFFFF", mix("FFFFFF", col["primary"], 0.85)),
            "tint": (col["tint"], col["secondary"], col["ink"], col["muted"]),
            "paper": ("FFFFFF", col["edge"], col["ink"], col["muted"]),
            "ghost": (None, col["edge"], col["ink"], col["muted"]),
        }[st]
        out = [{"p": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "line": line, "radius": el.get("radius", 3)}]
        size = el.get("size", 13)
        paras = []
        if el.get("title"):
            paras.append({"s": el["title"], "size": size, "bold": True, "head": True, "color": fg})
        if el.get("sub"):
            paras.append({"s": el["sub"], "size": el.get("subsize", max(10, size - 2.5)), "color": fg2})
        if paras:
            out.append({"p": "para", "x": x + 6, "y": y + 2, "w": w - 12, "h": h - 4, "paras": paras, "align": el.get("align", "c"), "anchor": el.get("anchor", "m")})
        return out
    if "flow" in el or "line" in el:
        flow = "flow" in el
        pts = [tuple(p) for p in el["flow" if flow else "line"]]
        c = col[el.get("color", "secondary" if flow else "edge")]
        out = [{"p": "poly", "points": pts, "color": c, "width": 2.2 if flow else 1.2, "flow": flow, "dash": flow or el.get("dash", False)}]
        if flow or el.get("arrow"):
            out.append({"p": "shape", "points": arrow_head(pts), "fill": c})
        return out
    if "text" in el:
        x, y = el["at"]
        para = {"s": el["text"], "size": el.get("size", 12), "bold": el.get("bold", False), "head": el.get("head", False), "color": col[el.get("color", "ink")]}
        return [{"p": "para", "x": x, "y": y, "w": el.get("w", 200), "h": el.get("h", el.get("size", 12) * 1.4), "paras": [para], "align": el.get("align", "l"), "anchor": el.get("anchor", "t")}]
    if "image" in el:
        png = rasterise(ddir, el["image"])
        x, y, w, h = fit(png, *el["box"])
        return [{"p": "image", "path": png, "poster": ddir / el["poster"] if "poster" in el else png, "x": x, "y": y, "w": w, "h": h}]
    if "icon" in el:
        png = rasterise(ddir, f"{ICONS}/{el['icon']}.svg", color=col[el.get("color", "primary")], px=192)
        x, y, w, h = el["box"]
        return [{"p": "image", "path": png, "poster": png, "x": x, "y": y, "w": w, "h": h}]
    if "dot" in el:
        x, y = el["dot"]
        r = el.get("r", 6)
        c = col[el.get("color", "primary")]
        if el.get("diamond"):
            return [{"p": "shape", "points": [(x, y - r), (x + r, y), (x, y + r), (x - r, y)], "fill": c}]
        return [{"p": "oval", "x": x - r, "y": y - r, "w": 2 * r, "h": 2 * r, "fill": c}]
    if "clear" in el:
        x, y, w, h = el["clear"]
        return [{"p": "rect", "x": x, "y": y, "w": w, "h": h, "fill": col["paper"], "line": None, "radius": 0}]
    sys.exit(f"diagram: unknown element {el}")


def layers(spec, col, ddir):
    """Primitives per step. A caption is a band at the bottom of the canvas, painted over the previous one."""
    W, H = spec["size"]
    out = []
    for step in spec["steps"]:
        ps = [p for el in step.get("draw", []) for p in prims(el, spec["size"], col, ddir)]
        if step.get("caption"):
            ps += prims({"clear": [0, H - CAPTION_H, W, CAPTION_H]}, spec["size"], col, ddir)
            ps += prims({"text": step["caption"], "at": [0, H - CAPTION_H], "w": W, "h": CAPTION_H, "size": 15, "anchor": "m"}, spec["size"], col, ddir)
        out.append(ps)
    return out


def svg_prim(p, faces, live):
    if p["p"] == "rect":
        fill = f'#{p["fill"]}' if p["fill"] else "none"
        stroke = f' stroke="#{p["line"]}" stroke-width="1"' if p["line"] else ""
        return f'<rect x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{p["h"]}" rx="{p["radius"]}" fill="{fill}"{stroke}/>'
    if p["p"] == "oval":
        return f'<circle cx="{p["x"] + p["w"] / 2}" cy="{p["y"] + p["h"] / 2}" r="{p["w"] / 2}" fill="#{p["fill"]}"/>'
    if p["p"] == "shape":
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in p["points"])
        return f'<polygon points="{pts}" fill="#{p["fill"]}"/>'
    if p["p"] == "poly":
        d = "M" + " L".join(f"{x} {y}" for x, y in p["points"])
        dash = ' stroke-dasharray="6 5"' if p["dash"] else ""
        out = f'<path d="{d}" fill="none" stroke="#{p["color"]}" stroke-width="{p["width"]}"{dash}>'
        if p["flow"] and live:  # the moving dash and the packet are the reference look: motion along the flow
            out += '<animate attributeName="stroke-dashoffset" from="22" to="0" dur="1.6s" repeatCount="indefinite"/></path>'
            out += f'<circle r="3.5" fill="#{p["color"]}"><animateMotion dur="3.2s" repeatCount="indefinite" path="{d}"/></circle>'
        else:
            out += "</path>"
        return out
    if p["p"] == "image":
        path = pathlib.Path(p["path"] if live else p["poster"])
        mime = {".gif": "gif", ".jpg": "jpeg", ".jpeg": "jpeg"}.get(path.suffix.lower(), "png")
        data = base64.b64encode(path.read_bytes()).decode()
        return f'<image x="{p["x"]:.1f}" y="{p["y"]:.1f}" width="{p["w"]:.1f}" height="{p["h"]:.1f}" href="data:image/{mime};base64,{data}"/>'
    # para
    lines = [(ln, q) for q in p["paras"] for ln in wrap(q["s"], p["w"], q["size"], q.get("head"))]
    heights = [q["size"] * 1.22 for _, q in lines]
    total = sum(heights)
    y = p["y"] + {"t": 0, "m": (p["h"] - total) / 2, "b": p["h"] - total}[p["anchor"]]
    anchor, x = {"l": ("start", p["x"]), "c": ("middle", p["x"] + p["w"] / 2), "r": ("end", p["x"] + p["w"])}[p["align"]]
    out = []
    for (ln, q), h in zip(lines, heights):
        y += h
        face = faces["head" if q.get("head") else "base"]
        weight = ' font-weight="600"' if q.get("bold") else ""
        out.append(f'<text x="{x:.1f}" y="{y - 0.26 * q["size"]:.1f}" text-anchor="{anchor}" font-size="{q["size"]}" font-family="{escape(face, quote=True)}"{weight} fill="#{q["color"]}">{escape(ln)}</text>')
    return "".join(out)


def svg(spec, lay, faces, upto=None):
    """upto=None: every step, live (fragments, motion). upto=n: steps 0..n, static, for rsvg-convert."""
    W, H = spec["size"]
    live = upto is None
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="dia" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    for i, ps in enumerate(lay if live else lay[:upto + 1]):
        frag = f' class="fragment" data-fragment-index="{i - 1}"' if live and i else ""
        out.append(f"<g{frag}>" + "".join(svg_prim(p, faces, live) for p in ps) + "</g>")
    return "".join(out) + "</svg>"


def fetch_icon(ddir, name):
    dst = ddir / ICONS / f"{name}.svg"
    if dst.exists():
        return
    if not re.fullmatch(r"[a-z0-9-]+", name):
        sys.exit(f"icon name {name!r} must match [a-z0-9-]+")
    dst.parent.mkdir(exist_ok=True)
    with urllib.request.urlopen(LUCIDE.format(name), timeout=30) as r:
        dst.write_bytes(r.read())


def deck_specs(ddir):
    text = "\n".join(q.read_text() for q in ddir.glob("*.qmd"))
    return re.findall(r'\.diagram[^}]*\bsrc="([^"]+)"', text), set(re.findall(r'\bicon="([a-z0-9-]+)"', text))


def main(ddir):
    srcs, icons = deck_specs(ddir)
    if not srcs and not icons:
        return
    proj = yaml.safe_load((ddir / "_quarto.yml").read_text()) or {}
    cfg, brand = load(pathlib.Path(proj["charter"]))
    col = palette(brand)
    fb = cfg.get("font_fallbacks", {})
    faces = {"head": ", ".join(font_stack(brand, "headings", fb)) + ", sans-serif", "base": ", ".join(font_stack(brand, "base", fb)) + ", sans-serif"}
    specs = {src: yaml.safe_load((ddir / src).read_text()) for src in srcs}
    for spec in specs.values():
        for step in spec["steps"]:
            for el in step.get("draw", []):
                if "icon" in el:
                    icons.add(el["icon"])
    for name in icons:
        fetch_icon(ddir, name)
        rasterise(ddir, f"{ICONS}/{name}.svg", color=col["primary"], px=192)
    (ddir / OUT).mkdir(exist_ok=True)
    for src, spec in specs.items():
        stem = pathlib.Path(src).stem
        lay = layers(spec, col, ddir)
        (ddir / OUT / f"{stem}.svg").write_text(svg(spec, lay, faces))
        (ddir / OUT / f"{stem}.steps").write_text(str(len(lay)))
        for n in range(len(lay)):
            subprocess.run(["rsvg-convert", "-f", "pdf", "-o", ddir / OUT / f"{stem}-{n}.pdf"], input=svg(spec, lay, faces, upto=n).encode(), check=True)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
