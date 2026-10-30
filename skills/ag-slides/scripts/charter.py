# /// script
# requires-python = ">=3.10"
# dependencies = ["python-pptx>=1.0", "pyyaml>=6"]
# ///
"""Project graphical charter for Quarto decks (pptx, beamer, revealjs) built from the project's own pptx template.

  charter.py build <charter_dir>                       template + _brand.yml + charter.yml -> <charter_dir>/build/
  charter.py deck <charter_dir> <deck_dir>             install or refresh the charter extension in a deck, write its _quarto.yml
  charter.py reference [<deck.qmd>]                    deck _reference.pptx with the deck footer filled (pre-render step;
                                                       the charter comes from `charter:` in the deck's _quarto.yml)

The pptx template is the source of truth: its master and layouts are rendered by PowerPoint into the backgrounds
that Beamer and revealjs use, and its placeholder geometry sets where titles, body and footer sit in every format.
"""
import argparse, pathlib, re, shutil, subprocess, sys
import yaml
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, PP_PLACEHOLDER
from pptx.util import Pt

HERE = pathlib.Path(__file__).resolve().parent
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main", "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
ROLES = ("title", "section", "content", "plain")
# layouts pandoc looks up by name in a reference doc
PANDOC_LAYOUTS = ("Title Slide", "Title and Content", "Section Header", "Two Content", "Comparison", "Content with Caption", "Blank")
JUSTIFY = {"l": "flex-start", "ctr": "center", "r": "flex-end", "just": "flex-start", "dist": "flex-start"}
FOOTER_TYPES = {PP_PLACEHOLDER.DATE: "left", PP_PLACEHOLDER.FOOTER: "center", PP_PLACEHOLDER.SLIDE_NUMBER: "right"}


def load(cdir):
    cfg = yaml.safe_load((cdir / "charter.yml").read_text())
    brand = yaml.safe_load((cdir / "_brand.yml").read_text())
    # the name becomes a directory, a Quarto format id and part of generated LaTeX and scss
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(cfg.get("name", ""))):
        sys.exit(f"charter.yml: name {cfg.get('name')!r} must match [A-Za-z0-9_-]+")
    return cfg, brand


def drop_slides(p):
    for sldId in list(p.slides._sldIdLst):
        p.part.drop_rel(sldId.rId)
        p.slides._sldIdLst.remove(sldId)


# presentation-level parts pandoc copies from a reference doc; it keeps the reference's rels file but drops
# every other part (customXml, handout master, revision and author logs, Google metadata), and PowerPoint
# then refuses to open the deck
PANDOC_KEEPS = ("/slide", "/slideMaster", "/notesMaster", "/theme", "/presProps", "/viewProps", "/tableStyles", "/font")


def save_reference(p, path):
    for rId, rel in list(p.part.rels.items()):
        if not rel.reltype.endswith(PANDOC_KEEPS):
            p.part.drop_rel(rId)
    for el in p.part._element.findall("p:handoutMasterIdLst", NS):
        p.part._element.remove(el)
    p.save(path)


def first_level(el):
    """The shape's lstStyle/lvl1pPr, created when missing."""
    a = lambda tag: f"{{{NS['a']}}}{tag}"
    body = el.find(".//p:txBody", NS)
    lst = body.find("a:lstStyle", NS)
    if lst is None:
        lst = body.makeelement(a("lstStyle"), {})
        body.insert(1, lst)  # after bodyPr
    lvl = lst.find("a:lvl1pPr", NS)
    if lvl is None:
        lvl = lst.makeelement(a("lvl1pPr"), {})
        lst.insert(0, lvl)
    return lvl


def set_text_color(el, hex_):
    """Every solid text fill of a shape becomes hex_; a shape that inherits its colour gets one at its first level."""
    fills = list(el.iterfind(".//a:solidFill", NS))
    if not fills:
        a = lambda tag: f"{{{NS['a']}}}{tag}"
        lvl = first_level(el)
        rpr = lvl.find("a:defRPr", NS)
        if rpr is None:
            rpr = lvl.makeelement(a("defRPr"), {})
            lvl.append(rpr)
        fills = [rpr.makeelement(a("solidFill"), {})]
        rpr.insert(1 if rpr.find("a:ln", NS) is not None else 0, fills[0])
    for sf in fills:
        sf.clear()
        sf.append(sf.makeelement(f"{{{NS['a']}}}srgbClr", {"val": hex_}))


def restyle(p, layouts, cfg, brand):
    """charter.yml `master:` and `restyle:` edit a template copy: master body text colour; per layout background,
    shape removal, placeholder width or box, text colour, font size and weight, alignment, picture opacity,
    added bars and static text.
    Bars are drawn on a scratch slide and moved into the layout: python-pptx cannot add shapes to a layout."""
    col = colors(brand)
    master = cfg.get("master") or {}
    if "body_color" in master:
        for sf in p.slide_masters[0]._element.iterfind(".//p:txStyles/p:bodyStyle//a:solidFill", NS):
            sf.clear()
            sf.append(sf.makeelement(f"{{{NS['a']}}}srgbClr", {"val": col[master["body_color"]]}))
    for r in cfg.get("restyle") or []:
        lay = layouts[r["layout"]]
        byname = {s.name: s for s in lay.shapes}
        if "background" in r:
            lay.background.fill.solid()
            lay.background.fill.fore_color.rgb = RGBColor.from_string(col[r["background"]])
        for name in r.get("remove", []):
            byname[name]._element.getparent().remove(byname[name]._element)
        for name, w in (r.get("width") or {}).items():
            byname[name].width = Pt(w)
        for name, (x, y, w, h) in (r.get("box") or {}).items():
            byname[name].left, byname[name].top, byname[name].width, byname[name].height = Pt(x), Pt(y), Pt(w), Pt(h)
        for name, al in (r.get("align") or {}).items():  # l, ctr, r on the first level of the shape's text
            first_level(byname[name]._element).set("algn", al)
            for ppr in byname[name]._element.iterfind(".//a:p/a:pPr", NS):
                ppr.set("algn", al)
        for name, c in (r.get("color") or {}).items():
            set_text_color(byname[name]._element, col[c])
        for name, f in (r.get("font") or {}).items():  # {size: pt, bold: bool} on the first level
            lvl = first_level(byname[name]._element)
            rpr = lvl.find("a:defRPr", NS)
            if rpr is None:
                rpr = lvl.makeelement(f"{{{NS['a']}}}defRPr", {})
                lvl.append(rpr)
            if "size" in f:
                rpr.set("sz", str(int(f["size"] * 100)))
            if "bold" in f:
                rpr.set("b", "1" if f["bold"] else "0")
        for name, opacity in (r.get("fade") or {}).items():
            blip = byname[name]._element.find(".//a:blip", NS)
            blip.append(blip.makeelement(f"{{{NS['a']}}}alphaModFix", {"amt": str(int(opacity * 1000))}))
        for bar in r.get("add", []):
            tmp = p.slides.add_slide(lay)
            if "text" in bar:  # static text, e.g. a funding statement
                tb = tmp.shapes.add_textbox(*(Pt(bar[k]) for k in ("x", "y", "w", "h")))
                tf = tb.text_frame
                tf.word_wrap = True
                for k in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
                    setattr(tf, k, 0)
                run = tf.paragraphs[0].add_run()
                run.text = bar["text"]
                run.font.size = Pt(bar.get("size", 10))
                run.font.bold = bar.get("bold", False)
                run.font.color.rgb = RGBColor.from_string(col[bar.get("color", "foreground")])
                lay.shapes._spTree.append(tb._element)
                drop_slides(p)
                continue
            kind = MSO_SHAPE.ROUNDED_RECTANGLE if bar.get("radius") else MSO_SHAPE.RECTANGLE
            shp = tmp.shapes.add_shape(kind, *(Pt(bar[k]) for k in ("x", "y", "w", "h")))
            if bar.get("radius"):
                shp.adjustments[0] = bar["radius"] / min(bar["w"], bar["h"])
            shp.line.fill.background()
            shp.shadow.inherit = False
            stops = [RGBColor.from_string(col[c]) for c in bar["fill"]]
            if len(stops) == 1:
                shp.fill.solid()
                shp.fill.fore_color.rgb = stops[0]
            else:  # top to bottom
                shp.fill.gradient()
                shp.fill.gradient_angle = 90
                for st, c in zip(shp.fill.gradient_stops, stops):
                    st.color.rgb = c
            lay.shapes._spTree.insert(2, shp._element)  # behind the placeholders
            drop_slides(p)


def open_template(cdir, cfg, brand):
    p = Presentation(cdir / cfg["template"])
    layouts = {l.name: l for m in p.slide_masters for l in m.slide_layouts}
    for name, src in (cfg.get("aliases") or {}).items():
        if name in layouts:
            sys.exit(f"alias {name!r}: the template already has a layout with that name")
        layouts[src].name = name
        layouts[name] = layouts.pop(src)
    drop_slides(p)
    restyle(p, layouts, cfg, brand)
    return p, layouts


def pt(emu):
    return round(emu / 12700, 1)


def run_props(el):
    """Size (pt) and colour of the first level of a placeholder or text style, when set there."""
    r = el.find(".//a:lvl1pPr/a:defRPr", NS) if el is not None else None
    if r is None:
        return {}
    out = {}
    if r.get("sz"):
        out["size"] = int(r.get("sz")) / 100
    # text fill only: effects (shadows, glows) carry their own srgbClr
    c = r.find("a:solidFill/a:srgbClr", NS)
    s = r.find("a:solidFill/a:schemeClr", NS)
    if c is not None:
        out["color"] = c.get("val")
    elif s is not None and s.get("val") in ("bg1", "lt1", "tx1", "dk1"):
        out["color"] = "FFFFFF" if s.get("val") in ("bg1", "lt1") else "000000"
    return out


def align_of(el):
    """Paragraph alignment (l, ctr, r) set on a placeholder's first level or first paragraph, else None."""
    if el is None:
        return None
    for path in (".//a:lstStyle/a:lvl1pPr", ".//a:p/a:pPr"):
        n = el.find(path, NS)
        if n is not None and n.get("algn"):
            return n.get("algn")
    return None


def geometry(p, layouts, cfg):
    """Placeholder boxes in points, per role, plus the master text sizes."""
    m = p.slide_masters[0]._element
    styles = {k: run_props(m.find(f".//p:txStyles/p:{k}", NS)) for k in ("titleStyle", "bodyStyle")}
    geo = {"slide": {"w": pt(p.slide_width), "h": pt(p.slide_height)}, "title_size": styles["titleStyle"].get("size", 44), "body_size": styles["bodyStyle"].get("size", 28)}
    master_ph = {ph.placeholder_format.type: ph for ph in p.slide_masters[0].placeholders}
    for role in ROLES:
        g = {}
        for ph in layouts[cfg["layouts"][role]].placeholders:
            t = ph.placeholder_format.type
            box = {"x": pt(ph.left), "y": pt(ph.top), "w": pt(ph.width), "h": pt(ph.height)}
            box |= run_props(master_ph[t]._element if t in master_ph else None) | run_props(ph._element)
            box |= {"align": align_of(ph._element) or align_of(master_ph[t]._element if t in master_ph else None) or {"left": "l", "center": "ctr", "right": "r"}.get(FOOTER_TYPES.get(t), "l")}
            if t in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE):
                g["title"] = box
            elif t in (PP_PLACEHOLDER.SUBTITLE, PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT) and "body" not in g:
                g["body"] = box
            elif t in FOOTER_TYPES:
                g[FOOTER_TYPES[t]] = box
        # title-only covers (REA): subtitle and author go in a box under the title
        if "title" in g and "body" not in g:
            ti = g["title"]
            g["body"] = {"x": ti["x"], "y": ti["y"] + ti["h"] + 8, "w": ti["w"], "h": 100}
        geo[role] = g
    return geo


def pptx2pdf(src, dst):
    subprocess.run([HERE / "pptx2pdf.sh", src, dst], check=True)


def render_backgrounds(p, layouts, cfg, out):
    """One slide per role with every placeholder removed: PowerPoint draws only the master decoration."""
    out.mkdir(parents=True, exist_ok=True)
    for role in ROLES:
        s = p.slides.add_slide(layouts[cfg["layouts"][role]])
        for ph in list(s.placeholders):
            ph._element.getparent().remove(ph._element)
    p.save(out / "backgrounds.pptx")
    pptx2pdf(out / "backgrounds.pptx", out / "backgrounds.pdf")
    for i, role in enumerate(ROLES, 1):
        subprocess.run(["pdfseparate", "-f", str(i), "-l", str(i), out / "backgrounds.pdf", out / f"{role}.pdf"], check=True)
        subprocess.run(["pdftoppm", "-png", "-singlefile", "-scale-to-x", "1920", "-scale-to-y", "1080", out / f"{role}.pdf", out / role], check=True)
    (out / "backgrounds.pptx").unlink()
    (out / "backgrounds.pdf").unlink()


def render_layout_sheet(cdir, cfg, brand, out):
    """Every template layout, labelled with its name, as one contact sheet: layout names lie, pictures do not."""
    p, layouts = open_template(cdir, cfg, brand)
    for name, lay in layouts.items():
        s = p.slides.add_slide(lay)
        for ph in s.placeholders:
            if ph.has_text_frame:
                ph.text_frame.text = name if ph.placeholder_format.type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE) else ""
    p.save(out / "layouts.pptx")
    pptx2pdf(out / "layouts.pptx", out / "layouts.pdf")
    (out / "layouts.pptx").unlink()


def font_stack(brand, key, fallbacks):
    ty = brand.get("typography", {})
    fam = ty[key] if isinstance(ty.get(key), str) else ty.get(key, {}).get("family")
    return list(dict.fromkeys([fam, *fallbacks.get(key, [])]))


def colors(brand):
    c = brand["color"]
    pal = c.get("palette", {})
    resolve = lambda v: pal.get(v, v).lstrip("#").upper()
    named = {k: resolve(v) for k, v in pal.items()}
    for k in ("foreground", "background", "primary", "secondary"):
        if k in c:
            named[k] = resolve(c[k])
    return named


def camel(k):
    return "".join(w.capitalize() for w in re.split(r"[-_]", k))


def write_beamer(cfg, brand, geo, out):
    """Beamer theme: backgrounds from PowerPoint, boxes from the template geometry, sizes scaled to the beamer page."""
    W, H = geo["slide"]["w"], geo["slide"]["h"]
    k = 160 / 25.4 * 72 / W  # template pt -> beamer pt on the 160 mm wide 16:9 page
    col = colors(brand)
    head, base = font_stack(brand, "headings", cfg.get("font_fallbacks", {})), font_stack(brand, "base", cfg.get("font_fallbacks", {}))
    pick = lambda fams, cs: "".join(f"\\IfFontExistsTF{{{f}}}{{{cs}{{{f}}}}}{{" for f in fams) + "}" * len(fams)
    frac = lambda v, tot: round(v / tot, 4)
    c, s, t = geo["content"], geo["section"], geo["title"]
    url = brand.get("meta", {}).get("link", "").split("//")[-1]
    L = [f"% Generated by ag-slides charter.py from the {cfg['name']} template. Edit the charter, then rebuild.",
         "\\ProvidesPackage{beamerthemecharter}",
         "\\RequirePackage{tikz}\\RequirePackage{iftex}",
         *[f"\\definecolor{{brand{camel(n)}}}{{HTML}}{{{v}}}" for n, v in col.items()],
         "\\ifLuaTeX\\RequirePackage{fontspec}",
         "  " + pick(base, "\\setsansfont"),
         "  " + pick(head, "\\newfontfamily\\brandhead"),
         "\\fi",
         "\\providecommand\\brandhead{\\sffamily}",
         "\\renewcommand{\\familydefault}{\\sfdefault}",
         "\\providecommand\\brandfooter{\\insertshortauthor}",
         "\\setbeamertemplate{navigation symbols}{}",
         "\\setbeamercolor{normal text}{fg=brandForeground}",
         "\\setbeamercolor{structure}{fg=brandPrimary}",
         "\\setbeamercolor{frametitle}{fg=brandPrimary}",
         "\\setbeamercolor{title}{fg=brandPrimary}",
         "\\setbeamertemplate{itemize items}{\\textbullet}",
         # figure captions carry credits: small, right-aligned, no "Figure n:" label
         # Quarto loads the caption package, which overrides beamer's caption template
         "\\setbeamertemplate{caption}{\\raggedleft\\tiny\\insertcaption\\par}",
         "\\AtBeginDocument{\\@ifpackageloaded{caption}{\\captionsetup{labelformat=empty,font=tiny,justification=raggedleft,singlelinecheck=false}}{}}",
         f"\\setbeamerfont{{frametitle}}{{family=\\brandhead,size=\\fontsize{{{geo['title_size']*k:.1f}}}{{{geo['title_size']*k*0.9:.1f}}}}}",
         f"\\renewcommand\\normalsize{{\\fontsize{{{geo['body_size']*k:.1f}}}{{{geo['body_size']*k*1.2:.1f}}}\\selectfont}}",
         "\\setbeamerfont{itemize/enumerate body}{size=\\normalsize}\\setbeamerfont{itemize/enumerate subbody}{size=\\small}",
         # pandoc writes tables as longtable; body size makes any 4-column table overflow
         "\\RequirePackage{etoolbox}\\AtBeginEnvironment{longtable}{\\footnotesize}",
         f"\\setbeamersize{{text margin left={c['body']['x']*k:.1f}pt,text margin right={(W-c['body']['x']-c['body']['w'])*k:.1f}pt}}",
         # frame title in the template's title box, bottom-anchored like the template
         f"\\setbeamertemplate{{frametitle}}{{\\vbox to {(c['title']['y']+c['title']['h'])*k:.1f}pt{{\\vfill\\insertframetitle\\par\\vspace{{2pt}}}}}}",
         "\\newcommand\\brandbg[1]{\\begin{tikzpicture}[remember picture,overlay]\\node[anchor=north west,inner sep=0] at (current page.north west) {\\includegraphics[width=\\paperwidth,height=\\paperheight]{#1}};\\end{tikzpicture}}",
         "\\newcommand\\brandistitle{\\ifnum\\value{framenumber}=1 \\ifx\\inserttitle\\empty\\else T\\fi\\fi}",
         "\\setbeamertemplate{background}{\\if T\\brandistitle\\brandbg{\\brandbgdir/title.pdf}\\else\\brandbg{\\brandbgdir/content.pdf}\\fi}",
         "\\newcommand\\brandfootbox[5]{\\node[anchor=north west,inner sep=0,text width=#3,align=#4,font=\\tiny,text=#5] at (#1,#2)}",
         "\\setbeamertemplate{footline}{\\if T\\brandistitle\\else\\begin{tikzpicture}[remember picture,overlay,x=\\paperwidth,y=-\\paperheight,shift={(current page.north west)}]",
         *[f"  \\brandfootbox{{{frac(c[pos]['x'],W)}}}{{{frac(c[pos]['y'],H)}}}{{{c[pos]['w']*k:.1f}pt}}{{{ {'l': 'left', 'ctr': 'center', 'r': 'right'}.get(c[pos]['align'], 'left') }}}{{brandFoot{pos}}}{{{text}}};"
           for pos, text in (("left", f"\\textbf{{{url}}}"), ("center", "\\brandfooter"), ("right", "\\insertframenumber")) if pos in c],
         "\\end{tikzpicture}\\fi}",
         # title page: template title slide, text placed in its title and subtitle boxes
         "\\setbeamertemplate{title page}{\\begin{tikzpicture}[remember picture,overlay,x=\\paperwidth,y=-\\paperheight,shift={(current page.north west)}]",
         f"  \\node[anchor=south west,inner sep=0,text width={t['title']['w']*k:.1f}pt,font=\\brandhead\\fontsize{{{t['title'].get('size',54)*k:.1f}}}{{{t['title'].get('size',54)*k:.1f}}}\\selectfont,text=brandTitle] (brandtitle) at ({frac(t['title']['x'],W)},{frac(t['title']['y']+t['title']['h'],H)}) {{\\inserttitle}};",
         "  \\ifdefined\\brandeyebrow\\node[anchor=south west,inner sep=0,font=\\scriptsize\\bfseries,text=brandSecondary] at ([yshift=6pt]brandtitle.north west) {\\MakeUppercase{\\brandeyebrow}};\\fi",
         f"  \\node[anchor=north west,inner sep=0,text width={t['body']['w']*k:.1f}pt,font=\\fontsize{{{t['body'].get('size',24)*k:.1f}}}{{{t['body'].get('size',24)*k*1.2:.1f}}}\\selectfont,text=brandSubtitle,align=left] at ({frac(t['body']['x'],W)},{frac(t['body']['y'],H)}) {{\\insertsubtitle\\\\[2pt]\\insertauthor\\\\\\insertinstitute}};",
         "\\end{tikzpicture}}",
         # section divider: template section layout
         "\\AtBeginSection{{\\setbeamertemplate{background}{\\brandbg{\\brandbgdir/section.pdf}}\\begin{frame}\\begin{tikzpicture}[remember picture,overlay,x=\\paperwidth,y=-\\paperheight,shift={(current page.north west)}]",
         f"  \\node[anchor=south west,inner sep=0,text width={s['title']['w']*k:.1f}pt,font=\\brandhead\\fontsize{{{s['title'].get('size',60)*k:.1f}}}{{{s['title'].get('size',60)*k:.1f}}}\\selectfont,text=brandSection] at ({frac(s['title']['x'],W)},{frac(s['title']['y']+s['title']['h'],H)}) {{\\insertsection}};",
         "\\end{tikzpicture}\\end{frame}}}",
         ]
    L.insert(3, f"\\definecolor{{brandTitle}}{{HTML}}{{{t['title'].get('color') or col['foreground']}}}")
    L.insert(3, f"\\definecolor{{brandSubtitle}}{{HTML}}{{{t['body'].get('color') or col['background']}}}")
    for pos in ("left", "center", "right"):
        if pos in c:
            L.insert(3, f"\\definecolor{{brandFoot{pos}}}{{HTML}}{{{c[pos].get('color') or col['secondary']}}}")
    L.insert(3, f"\\definecolor{{brandSection}}{{HTML}}{{{s['title'].get('color') or col['primary']}}}")
    (out / "beamerthemecharter.sty").write_text("\n".join(L) + "\n")


def write_scss(cfg, brand, geo, out):
    """revealjs theme: brand colours and fonts, template boxes as percentages of the slide."""
    W, H = geo["slide"]["w"], geo["slide"]["h"]
    px = lambda v: f"{v * 1600 / W:.0f}px"  # decks render at 1600x900
    pc = lambda v, tot: f"{100 * v / tot:.2f}%"
    col = colors(brand)
    stack = lambda key: ", ".join(f'"{f}"' for f in font_stack(brand, key, cfg.get("font_fallbacks", {}))) + ", sans-serif"
    c, s, t = geo["content"], geo["section"], geo["title"]
    # PowerPoint insets text 7.2 pt left and right, 3.6 pt top and bottom inside a placeholder
    inset = f"padding: {px(3.6)} {px(7.2)}; box-sizing: border-box;"
    box = lambda b: f"position: absolute; left: {pc(b['x'], W)}; top: {pc(b['y'], H)}; width: {pc(b['w'], W)}; height: {pc(b['h'], H)}; margin: 0; {inset}"
    foot = lambda pos, cls, extra="": (f".reveal .brand-foot .{cls} {{ left: {px(c[pos]['x'])}; top: {px(c[pos]['y'])}; width: {px(c[pos]['w'])}; height: {px(c[pos]['h'])}; {extra} }}"
                                        if pos in c else f".reveal .brand-foot .{cls} {{ display: none; }}")
    ref = c.get("center") or c.get("right") or {}
    # footer text keeps the template placeholder's alignment and colour
    fjust = lambda pos: (f"justify-content: {JUSTIFY[c[pos]['align']]}; color: #{c[pos].get('color') or col['secondary']};" if pos in c else "")
    # Google faces from _brand.yml load in the browser; LaTeX and PowerPoint use their own fallbacks
    google = [f for f in brand.get("typography", {}).get("fonts", []) if f.get("source") == "google"]
    fonts = "&".join(f"family={f['family'].replace(' ', '+')}" + (f":wght@{';'.join(map(str, sorted(f['weight'])))}" if f.get("weight") else "") for f in google)
    css = f"""/*-- scss:defaults --*/
// Generated by ag-slides charter.py from the {cfg['name']} template. Edit the charter, then rebuild.
{f"@import url('https://fonts.googleapis.com/css2?{fonts}&display=swap');" if google else ""}
{chr(10).join(f'$brand-{n}: #{v};' for n, v in col.items())}
$body-bg: #{col['background']};
$body-color: #{col['foreground']};
$link-color: #{col['primary']};
$presentation-heading-color: #{col['primary']};
$font-family-sans-serif: {stack('base')};
$presentation-heading-font: {stack('headings')};
$presentation-heading-font-weight: normal;
// PowerPoint shrinks body text to fit its box, revealjs does not
$presentation-font-size-root: {px(geo['body_size'] * 0.8)};

/*-- scss:rules --*/
.reveal .slides section.slide.level2 > h2 {{ {box(c['title'])} display: flex; align-items: flex-end; font-size: {px(geo['title_size'])}; line-height: 0.9; }}
.reveal .slides section.slide.level2 {{ padding-top: {px(c['body']['y'])} !important; padding-left: {px(c['body']['x'])}; padding-right: {px(W - c['body']['x'] - c['body']['w'])}; box-sizing: border-box; height: 100%; }}
.reveal .slides section.title-slide.level1 > h1 {{ {box(s['title'])} display: flex; align-items: flex-end; font-size: {px(s['title'].get('size', 60))}; color: #{s['title'].get('color') or col['primary']}; }}
#title-slide .title {{ {box(t['title'])} display: flex; flex-direction: column; justify-content: flex-end; align-items: flex-start; font-size: {px(t['title'].get('size', 54))}; color: #{t['title'].get('color') or col['foreground']}; text-align: left; }}
// subtitle, authors and institute flow down from the body box top, so a wrapped subtitle pushes the rest down
// Quarto marks the title slide `center`: reveal then shifts it down and shrinks it; pin it to the template box
#title-slide {{ top: 0 !important; height: 100% !important; box-sizing: border-box; padding: {px(t['body']['y'] + 3.6)} {px(W - t['body']['x'] - t['body']['w'] + 7.2)} 0 {px(t['body']['x'] + 7.2)} !important; text-align: left; }}
#title-slide .subtitle, #title-slide .quarto-title-authors {{ position: static; margin: 0; color: #{t['body'].get('color') or col['background']}; text-align: left; font-size: {px(t['body'].get('size', 24))}; }}
#title-slide .quarto-title-authors {{ display: block; margin-top: 0.6em; font-size: {px(t['body'].get('size', 24) * 0.7)}; line-height: 1.5; }}
#title-slide .quarto-title-author {{ padding: 0; }}
#title-slide .quarto-title-author-name, #title-slide .quarto-title-affiliation {{ margin: 0; }}
.reveal table {{ font-size: 0.65em; }}
// footer drawn inside each slide (charter.lua), so it scales with the slide instead of sticking to the window edges
.reveal .footer, .reveal .slide-number {{ display: none !important; }}
.reveal .slides section.slide {{ height: 100%; box-sizing: border-box; }}
.reveal .brand-foot > span {{ position: absolute; display: flex; align-items: center; color: #{ref.get('color') or col['secondary']}; font-size: {px(ref.get('size', 12))}; line-height: 1; }}
{foot('left', 'brand-url', fjust('left') + ' font-weight: bold;')}
.reveal .brand-foot .brand-url::after {{ content: "{brand.get('meta', {}).get('link', '').split('//')[-1]}"; }}
{foot('center', 'brand-text', fjust('center'))}
{foot('right', 'brand-num', fjust('right'))}
"""
    (out / f"{cfg['name']}.scss").write_text(css)


def write_extension(cfg, ext):
    """Quarto format extension: `format: <name>-pptx | <name>-beamer | <name>-revealjs` in a deck."""
    shutil.copy(HERE / "charter.lua", ext / "charter.lua")
    shutil.copy(HERE / "components.scss", ext / "components.scss")
    shutil.copytree(HERE / "vendor" / "pointer", ext / "pointer")
    spec = {
        "title": f"{cfg['name']} charter",
        "author": "ag-slides charter.py (generated, do not edit)",
        "quarto-required": ">=1.6.0",
        "contributes": {"formats": {
            "common": {"filters": ["charter.lua"]},
            # deck-local reference doc: the pre-render step writes it with the deck footer filled
            "pptx": {"reference-doc": "_reference.pptx"},
            # no embed-resources: Quarto refuses chalkboard in self-contained output (slides.html + slides_files/)
            "revealjs": {"theme": ["default", f"{cfg['name']}.scss", "components.scss"], "width": 1600, "height": 900,
                         "transition": "fade", "transition-speed": "fast", "background-transition": "fade",
                         # margin 0: the slide fills the same letterboxed box as the `contain` background
                         "slide-number": False, "center": False, "controls": False, "margin": 0,
                         "chalkboard": {"theme": "whiteboard"}, "revealjs-plugins": ["pointer"]},
            "beamer": {"aspectratio": 169, "pdf-engine": "lualatex", "classoption": ["t"]},
        }},
    }
    (ext / "_extension.yml").write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True))


def build(cdir):
    cfg, brand = load(cdir)
    out = cdir / "build"
    if out.exists():
        shutil.rmtree(out)
    ext = out / "_extensions" / cfg["name"]
    ext.mkdir(parents=True)
    p, layouts = open_template(cdir, cfg, brand)
    missing = [n for n in PANDOC_LAYOUTS if n not in layouts]
    if missing:
        sys.exit(f"pandoc needs these layout names, alias them in charter.yml: {missing}")
    geo = geometry(p, layouts, cfg)
    save_reference(p, out / "reference-base.pptx")
    render_backgrounds(p, layouts, cfg, ext / "backgrounds")
    render_layout_sheet(cdir, cfg, brand, out)
    write_beamer(cfg, brand, geo, ext)
    write_scss(cfg, brand, geo, ext)
    write_extension(cfg, ext)
    (out / "geometry.yml").write_text(yaml.safe_dump(geo, sort_keys=False))
    print(f"charter {cfg['name']} built in {out}")


def front_matter(qmd):
    m = re.match(r"^---\n(.*?)\n---\n", qmd.read_text(), re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def reference(qmd):
    # Quarto splits pre-render commands on whitespace without a shell: paths go through _quarto.yml, not argv
    proj = yaml.safe_load((qmd.parent / "_quarto.yml").read_text()) or {}
    cdir = pathlib.Path(proj.get("charter") or sys.exit(f"{qmd.parent}/_quarto.yml: no `charter:` key, run `charter.py deck` again"))
    fm = front_matter(qmd)
    footer = fm.get("footer") or sys.exit(f"{qmd}: set `footer:` in the front matter, it fills the pptx, beamer and revealjs footers")
    p = Presentation(cdir / "build" / "reference-base.pptx")
    for m in p.slide_masters:
        for el in [m, *m.slide_layouts]:
            for ph in el.placeholders:
                if ph.placeholder_format.type == PP_PLACEHOLDER.FOOTER:
                    runs = [r for para in ph.text_frame.paragraphs for r in para.runs]
                    runs[0].text = footer
                    for r in runs[1:]:
                        r.text = ""
    p.save(qmd.parent / "_reference.pptx")


def hook(proj, key, cmd, mark):
    """Add cmd to a Quarto pre/post-render hook, keeping the deck's own entries; an older form of cmd (same mark) is replaced."""
    cur = proj.get(key) or []
    cur = [c for c in ([cur] if isinstance(cur, str) else cur) if mark not in c]
    proj[key] = cur + [cmd] if cur else cmd


def deck(cdir, ddir):
    cfg, _ = load(cdir)
    src = cdir / "build" / "_extensions" / cfg["name"]
    if not src.exists():
        sys.exit(f"{src} missing: run `charter.py build {cdir}` first")
    dst = ddir / "_extensions" / cfg["name"]
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    script = pathlib.Path(__file__).resolve()
    if re.search(r"\s", str(script)):
        sys.exit(f"{script}: Quarto splits pre-render commands on whitespace, install the skill on a path without spaces")
    q = ddir / "_quarto.yml"
    conf = (yaml.safe_load(q.read_text()) or {}) if q.exists() else {}
    proj = conf.setdefault("project", {})
    proj.setdefault("output-dir", "build")
    # revealjs backgrounds referenced by relative path: copy them into build/ so it stays self-sufficient
    proj.setdefault("resources", [f"_extensions/{cfg['name']}/backgrounds/*.png"])
    hook(proj, "pre-render", f"uv run {script} reference", "charter.py reference")
    # pptx: tiles, cards and steps redrawn as shapes after pandoc (pptx_components.py)
    hook(proj, "post-render", f"uv run {script.parent / 'pptx_components.py'}", "pptx_components.py")
    conf["charter"] = str(cdir)
    q.write_text(yaml.safe_dump(conf, sort_keys=False))
    print(f"{cfg['name']} extension installed in {dst}; formats: {cfg['name']}-pptx, {cfg['name']}-beamer, {cfg['name']}-revealjs")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").add_argument("charter", type=pathlib.Path)
    d = sub.add_parser("deck")
    d.add_argument("charter", type=pathlib.Path)
    d.add_argument("deck", type=pathlib.Path)
    r = sub.add_parser("reference")
    r.add_argument("qmd", type=pathlib.Path, nargs="?", default=pathlib.Path("slides.qmd"))
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.charter.resolve())
    elif a.cmd == "deck":
        deck(a.charter.resolve(), a.deck.resolve())
    else:
        reference(a.qmd.resolve())
