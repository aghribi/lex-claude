# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10"]
# ///
"""Contact sheet of a rendered deck, one row per format: pptx (through PowerPoint), beamer pdf, revealjs (Chrome screenshots).

  compare.py <deck_dir> [--stem slides] [--out compare.png]

Read the sheet before calling a deck done: same slides, same order, nothing clipped, footer filled.
"""
import argparse, pathlib, re, subprocess, tempfile
from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 400, 225

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("deck", type=pathlib.Path)
ap.add_argument("--stem", default="slides")
ap.add_argument("--out", type=pathlib.Path)
a = ap.parse_args()
d = a.deck.resolve()
d = d / "build" if (d / "build" / f"{a.stem}.html").exists() or (d / "build" / f"{a.stem}.pptx").exists() else d
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ag-slides-"))


def pdf_pages(pdf, tag):
    subprocess.run(["pdftoppm", "-png", "-scale-to-x", str(W), "-scale-to-y", str(H), pdf, tmp / tag], check=True)
    return sorted(tmp.glob(f"{tag}-*.png"))


rows = {}
if (d / f"{a.stem}.pptx").exists():
    subprocess.run([HERE / "pptx2pdf.sh", d / f"{a.stem}.pptx", tmp / "pptx.pdf"], check=True, stdout=subprocess.DEVNULL)
    rows["pptx"] = pdf_pages(tmp / "pptx.pdf", "pptx")
if (d / f"{a.stem}.pdf").exists():
    rows["beamer"] = pdf_pages(d / f"{a.stem}.pdf", "beamer")
if (d / f"{a.stem}.html").exists():
    # navigate by section id: `#` headings open vertical stacks, so index hashes do not reach every slide;
    # reveal reads config overrides from the query string: fragments=false shows every fragment
    ids = re.findall(r'<section\b[^>]*\bid="([^"]+)"', (d / f"{a.stem}.html").read_text())
    shots = []
    for i, sid in enumerate(ids):
        png = tmp / f"reveal-{i:03d}.png"
        subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--window-size=1600,900", "--virtual-time-budget=6000",
                        f"--screenshot={png}", f"file://{d / a.stem}.html?fragments=false#/{sid}"], check=True, capture_output=True)
        shots.append(png)
    rows["revealjs"] = shots

n = max(len(v) for v in rows.values())
sheet = Image.new("RGB", (60 + W * n, H * len(rows)), "white")
draw = ImageDraw.Draw(sheet)
for j, (fmt, pages) in enumerate(rows.items()):
    draw.text((4, j * H + H // 2), fmt, fill="black")
    for i, p in enumerate(pages):
        sheet.paste(Image.open(p).convert("RGB").resize((W, H)), (60 + i * W, j * H))
out = a.out or d / f"{a.stem}_compare.png"
sheet.save(out)
print(out, {k: len(v) for k, v in rows.items()})
