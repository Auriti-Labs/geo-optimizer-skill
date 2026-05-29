from __future__ import annotations

import os
from pathlib import Path

# Set GEO_STATIC_DIR before any web app module import so StaticFiles finds
# the Astro dist directory. Without this, FastAPI returns 404 on GET /.
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
# In CI the Astro frontend is not built, so the dist directory is absent.
# StaticFiles(directory=...) raises RuntimeError at import time if it is
# missing, which importorskip cannot catch. Create an empty placeholder so
# the web app module imports cleanly during collection.
_FRONTEND_DIST.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("GEO_STATIC_DIR", str(_FRONTEND_DIST))
