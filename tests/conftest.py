from __future__ import annotations

import os
from pathlib import Path

# Set GEO_STATIC_DIR before any web app module import so StaticFiles finds
# the Astro dist directory. Without this, FastAPI returns 404 on GET /.
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
os.environ.setdefault("GEO_STATIC_DIR", str(_FRONTEND_DIST))
