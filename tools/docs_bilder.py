"""Verkleinert die Roh-Screenshots aus tests/docs-bilder.spec.js (doppelte Auflösung) zu den Bildern in docs/.

  DOCS=1 npx playwright test docs-bilder && python3 tools/docs_bilder.py
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
for src in sorted((ROOT / "konzepte/docs_roh").glob("*.png")):
    im = Image.open(src).convert("RGB")
    im = im.resize((1600, round(1600 * im.height / im.width)), Image.LANCZOS)
    out = ROOT / "docs" / (src.stem + ".jpg")
    out.parent.mkdir(exist_ok=True)
    im.save(out, quality=86, optimize=True, progressive=True)
    print(out.relative_to(ROOT), im.size, f"{out.stat().st_size // 1024} KB")
