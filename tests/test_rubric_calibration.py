"""Taratura: nessun sito "sano" perde più di 15 punti da v1 a v2 senza un fail G-* che lo motivi.

Le fixture sono HTML di terzi catturate con scripts/capture_calibration_fixtures.py e restano locali
(gitignored): senza fixture il test viene saltato.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

import pytest

from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.models.results import CdnAiCrawlerResult

FIX = Path(__file__).parent / "fixtures" / "calibration"
CASES = sorted(p.stem for p in FIX.glob("*.json")) if FIX.exists() else []
MAX_UNEXPLAINED_DROP = 15


def _fake_fetch(meta, html):
    def fetch(url, *a, **kw):
        path = urlsplit(url).path
        if path in meta["files"]:
            text = meta["files"][path]
            if text is None:
                return None, "404"
            return MagicMock(status_code=200, text=text, content=text.encode(), headers={}), None
        if url.rstrip("/") == meta["url"].rstrip("/"):
            resp = MagicMock(
                status_code=meta["status"],
                text=html,
                content=html.encode(),
                headers=meta["headers"],
                url=meta["final_url"],
            )
            return resp, None
        return None, "not captured"

    return fetch


def _audit(meta, html, version):
    fetch = patch("geo_optimizer.core.audit.fetch_url", side_effect=_fake_fetch(meta, html))
    markdown = patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False)
    cdn = patch("geo_optimizer.core.audit.audit_cdn_ai_crawler", return_value=CdnAiCrawlerResult())
    with fetch, markdown, cdn:
        return run_full_audit(meta["url"], score_version=version)


@pytest.mark.skipif(not CASES, reason="no calibration fixtures captured")
@pytest.mark.parametrize("slug", CASES)
def test_v2_drop_is_explained(slug):
    meta = json.loads((FIX / f"{slug}.json").read_text(encoding="utf-8"))
    html = (FIX / f"{slug}.html").read_text(encoding="utf-8")
    v1 = _audit(meta, html, 1)
    v2 = _audit(meta, html, 2)
    assert not v1.error and not v2.error, f"{slug}: {v1.error or v2.error}"
    drop = v1.score - v2.score
    fails = [c.id for c in v2.google_ai.checks if c.status == "fail"]
    assert drop <= MAX_UNEXPLAINED_DROP or fails, f"{slug}: v1 {v1.score} → v2 {v2.score} (-{drop}) with no Google fail"
