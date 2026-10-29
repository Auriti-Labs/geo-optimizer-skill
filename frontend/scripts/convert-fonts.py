#!/usr/bin/env python3
"""convert-fonts — converte i font woff2 in TTF per satori (og:image post-build).

satori non accetta WOFF2 (richiede TTF/OTF). Usa fontTools per generare i TTF
in public/fonts/ttf/ dai woff2. Invocato da generate-og-images.mjs (postbuild).
"""
from fontTools.ttLib import TTFont
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "public" / "fonts"
DST = SRC / "ttf"
DST.mkdir(parents=True, exist_ok=True)

FONTS = {
    "geist-latin-600-normal.woff2": "geist-semibold.ttf",
    "geist-latin-400-normal.woff2": "geist-regular.ttf",
}

for src, dst in FONTS.items():
    try:
        f = TTFont(str(SRC / src))
        f.flavor = None
        f.save(str(DST / dst))
        print("ok", dst)
    except Exception as e:
        print("ERR", src, e, file=sys.stderr)
        sys.exit(1)
print("[convert-fonts] OK")
