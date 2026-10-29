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
from pptx.enum.shapes import PP_PLACEHOLDER

HERE = pathlib.Path(__file__).resolve().parent
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main", "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
ROLES = ("title", "section", "content", "plain")
# layouts pandoc looks up by name in a reference doc
PANDOC_LAYOUTS = ("Title Slide", "Title and Content", "Section Header", "Two Content", "Comparison", "Content with Caption", "Blank")
FOOTER_TYPES = {PP_PLACEHOLDER.DATE: "left", PP_PLACEHOLDER.FOOTER: "center", PP_PLACEHOLDER.SLIDE_NUMBER: "right"}


def load(cdir):
    cfg = yaml.safe_load((cdir / "charter.yml").read_text())
    brand = yaml.safe_load((cdir / "_brand.yml").read_text())
    # the name becomes a directory, a Quarto format id and part of generated LaTeX and scss
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(cfg.get("name", ""))):
        sys.exit(f"charter.yml: name {cfg.get('name')!r} must match [A-Za-z0-9_-]+")
    return cfg, brand


def open_template(cdir, cfg):
    p = Presentation(cdir / cfg["template"])
    layouts = {l.name: l for m in p.slide_masters for l in m.slide_layouts}
    for name, src in (cfg.get("aliases") or {}).items():
        if name in layouts:
            sys.exit(f"alias {name!r}: the template already has a layout with that name")
        layouts[src].name = name
        layouts[name] = layouts.pop(src)
    for sldId in list(p.slides._sldIdLst):
        p.part.drop_rel(sldId.rId)
        p.slides._sldIdLst.remove(sldId)
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
    c = r.find(".//a:srgbClr", NS)
    if c is not None:
        out["color"] = c.get("val")
    return out


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


def render_layout_sheet(cdir, cfg, out):
    """Every template layout, labelled with its name, as one contact sheet: layout names lie, pictures do not."""
    p, layouts = open_template(cdir, cfg)
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
         "\\newcommand\\brandfootbox[4]{\\node[anchor=north west,inner sep=0,text width=#3,align=#4,font=\\tiny,text=brandSecondary] at (#1,#2)}",
         "\\setbeamertemplate{footline}{\\if T\\brandistitle\\else\\begin{tikzpicture}[remember picture,overlay,x=\\paperwidth,y=-\\paperheight,shift={(current page.north west)}]",
         *[f"  \\brandfootbox{{{frac(c[pos]['x'],W)}}}{{{frac(c[pos]['y'],H)}}}{{{c[pos]['w']*k:.1f}pt}}{{{pos}}}{{{text}}};"
           for pos, text in (("left", f"\\textbf{{{url}}}"), ("center", "\\brandfooter"), ("right", "\\insertframenumber")) if pos in c],
         "\\end{tikzpicture}\\fi}",
         # title page: template title slide, text placed in its title and subtitle boxes
         "\\setbeamertemplate{title page}{\\begin{tikzpicture}[remember picture,overlay,x=\\paperwidth,y=-\\paperheight,shift={(current page.north west)}]",
         f"  \\node[anchor=south west,inner sep=0,text width={t['title']['w']*k:.1f}pt,font=\\brandhead\\fontsize{{{t['title'].get('size',54)*k:.1f}}}{{{t['title'].get('size',54)*k:.1f}}}\\selectfont,text=brandTitle] at ({frac(t['title']['x'],W)},{frac(t['title']['y']+t['title']['h'],H)}) {{\\inserttitle}};",
         f"  \\node[anchor=north west,inner sep=0,text width={t['body']['w']*k:.1f}pt,font=\\fontsize{{{t['body'].get('size',24)*k:.1f}}}{{{t['body'].get('size',24)*k*1.2:.1f}}}\\selectfont,text=brandBackground,align=left] at ({frac(t['body']['x'],W)},{frac(t['body']['y'],H)}) {{\\insertsubtitle\\\\[2pt]\\insertauthor\\\\\\insertinstitute}};",
         "\\end{tikzpicture}}",
         # section divider: template section layout
         "\\AtBeginSection{{\\setbeamertemplate{background}{\\brandbg{\\brandbgdir/section.pdf}}\\begin{frame}\\begin{tikzpicture}[remember picture,overlay,x=\\paperwidth,y=-\\paperheight,shift={(current page.north west)}]",
         f"  \\node[anchor=south west,inner sep=0,text width={s['title']['w']*k:.1f}pt,font=\\brandhead\\fontsize{{{s['title'].get('size',60)*k:.1f}}}{{{s['title'].get('size',60)*k:.1f}}}\\selectfont,text=brandForeground] at ({frac(s['title']['x'],W)},{frac(s['title']['y']+s['title']['h'],H)}) {{\\insertsection}};",
         "\\end{tikzpicture}\\end{frame}}}",
         ]
    L.insert(3, f"\\definecolor{{brandTitle}}{{HTML}}{{{t['title'].get('color') or col['foreground']}}}")
    (out / "beamerthemecharter.sty").write_text("\n".join(L) + "\n")


def write_scss(cfg, brand, geo, out):
    """revealjs theme: brand colours and fonts, template boxes as percentages of the slide."""
    W, H = geo["slide"]["w"], geo["slide"]["h"]
    px = lambda v: f"{v * 1600 / W:.0f}px"  # decks render at 1600x900
    pc = lambda v, tot: f"{100 * v / tot:.2f}%"
    col = colors(brand)
    stack = lambda key: ", ".join(f'"{f}"' for f in font_stack(brand, key, cfg.get("font_fallbacks", {}))) + ", sans-serif"
    c, s, t = geo["content"], geo["section"], geo["title"]
    box = lambda b: f"position: absolute; left: {pc(b['x'], W)}; top: {pc(b['y'], H)}; width: {pc(b['w'], W)}; height: {pc(b['h'], H)}; margin: 0;"
    foot = lambda pos, cls, extra="": (f".reveal .brand-foot .{cls} {{ left: {px(c[pos]['x'])}; top: {px(c[pos]['y'])}; width: {px(c[pos]['w'])}; height: {px(c[pos]['h'])}; {extra} }}"
                                        if pos in c else f".reveal .brand-foot .{cls} {{ display: none; }}")
    ref = c.get("center") or c.get("right") or {}
    css = f"""/*-- scss:defaults --*/
// Generated by ag-slides charter.py from the {cfg['name']} template. Edit the charter, then rebuild.
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
.reveal .slides section.title-slide.level1 > h1 {{ {box(s['title'])} display: flex; align-items: flex-end; font-size: {px(s['title'].get('size', 60))}; }}
#title-slide .title {{ {box(t['title'])} display: flex; align-items: flex-end; font-size: {px(t['title'].get('size', 54))}; color: #{t['title'].get('color') or col['foreground']}; text-align: left; }}
#title-slide .subtitle, #title-slide .quarto-title-authors {{ color: #{col['background']}; text-align: left; font-size: {px(t['body'].get('size', 24))}; }}
#title-slide .quarto-title-block-meta, #title-slide .subtitle {{ position: absolute; left: {pc(t['body']['x'], W)}; width: {pc(t['body']['w'], W)}; }}
#title-slide .subtitle {{ top: {pc(t['body']['y'], H)}; }}
#title-slide .quarto-title-authors {{ position: absolute; left: {pc(t['body']['x'], W)}; top: calc({pc(t['body']['y'], H)} + 1.4em); justify-content: flex-start; }}
#title-slide .quarto-title-author {{ padding: 0; }}
.reveal table {{ font-size: 0.65em; }}
// footer drawn inside each slide (charter.lua), so it scales with the slide instead of sticking to the window edges
.reveal .footer, .reveal .slide-number {{ display: none !important; }}
.reveal .slides section.slide {{ height: 100%; box-sizing: border-box; }}
.reveal .brand-foot > span {{ position: absolute; display: flex; align-items: center; color: #{ref.get('color') or col['secondary']}; font-size: {px(ref.get('size', 12))}; line-height: 1; }}
{foot('left', 'brand-url', 'font-weight: bold;')}
.reveal .brand-foot .brand-url::after {{ content: "{brand.get('meta', {}).get('link', '').split('//')[-1]}"; }}
{foot('center', 'brand-text', 'justify-content: center;')}
{foot('right', 'brand-num', 'justify-content: flex-end; color: #' + ((c.get('right') or {}).get('color') or col['secondary']) + ';')}
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
                         "slide-number": False, "center": False, "controls": False,
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
    p, layouts = open_template(cdir, cfg)
    missing = [n for n in PANDOC_LAYOUTS if n not in layouts]
    if missing:
        sys.exit(f"pandoc needs these layout names, alias them in charter.yml: {missing}")
    geo = geometry(p, layouts, cfg)
    p.save(out / "reference-base.pptx")
    render_backgrounds(p, layouts, cfg, ext / "backgrounds")
    render_layout_sheet(cdir, cfg, out)
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
    proj["pre-render"] = f"uv run {script} reference"
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
