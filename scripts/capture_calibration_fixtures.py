"""Cattura fixture di taratura rubric v1↔v2 (rete reale, solo dev).

Uso: python scripts/capture_calibration_fixtures.py URL [URL...]
Le fixture finiscono in tests/fixtures/calibration/ (gitignored: HTML di terzi, mai committato).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from geo_optimizer.utils.http import fetch_url

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "calibration"
# Header che possono contenere identificativi di sessione: non salvarli
_DROP_HEADERS = {"set-cookie", "cookie"}
# File di sito che l'audit legge oltre alla pagina: senza, v1 perderebbe llms.txt a tavolino
_SITE_FILES = (
    "/robots.txt",
    "/llms.txt",
    "/llms-full.txt",
    "/.well-known/ai.txt",
    "/ai/summary.json",
    "/ai/faq.json",
    "/ai/service.json",
)


def main(urls: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for url in urls:
        r, err = fetch_url(url)
        if err or r is None or r.status_code != 200:
            print(f"skip {url}: {err or (r.status_code if r is not None else 'no response')}")
            continue
        files = {}
        for path in _SITE_FILES:
            f, _ = fetch_url(urljoin(url, path))
            files[path] = f.text if f is not None and f.status_code == 200 else None
        slug = re.sub(r"[^a-z0-9]+", "-", url.lower().split("://", 1)[-1]).strip("-")[:60]
        headers = {k: v for k, v in dict(r.headers).items() if k.lower() not in _DROP_HEADERS}
        (OUT / f"{slug}.html").write_text(r.text, encoding="utf-8")
        meta = {
            "url": url,
            "final_url": str(getattr(r, "url", "") or url),
            "status": r.status_code,
            "headers": headers,
            "files": files,
        }
        (OUT / f"{slug}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"ok {slug} ({r.status_code})")


if __name__ == "__main__":
    main(sys.argv[1:])
