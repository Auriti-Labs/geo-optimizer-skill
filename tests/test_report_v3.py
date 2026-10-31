"""Report HTML/PDF v3: cached results keep the v2 rubric, no emoji glyphs, embedded Stack Sans."""

from __future__ import annotations

import re
import zlib

import pytest

# publish.yml installs only .[dev]: without this the tag build fails at collection
pytest.importorskip("fastapi", reason="FastAPI non installato (pip install geo-optimizer-skill[web])")

from geo_optimizer.cli.html_formatter import format_audit_html
from geo_optimizer.models.results import AuditResult, GoogleAiReadinessResult, ReadinessCheck
from geo_optimizer.web.app import _audit_result_to_dict, _dict_to_audit_result


def _v2_result() -> AuditResult:
    return AuditResult(
        url="https://example.com",
        score=94,
        band="excellent",
        score_version=2,
        score_max={"google_ai": 20, "content": 14},
        score_breakdown={"google_ai": 18, "content": 14},
        google_ai=GoogleAiReadinessResult(
            checked=True,
            points=18,
            max_points=20,
            checks=[ReadinessCheck("G-INDEX", "fail", 0, 5, "noindex", "https://developers.google.com/")],
        ),
    )


def test_cached_result_keeps_v2_rubric_and_google_ai():
    rebuilt = _dict_to_audit_result(_audit_result_to_dict(_v2_result()))
    assert rebuilt.score_version == 2
    assert rebuilt.score_max == {"google_ai": 20, "content": 14}
    assert [c.id for c in rebuilt.google_ai.checks] == ["G-INDEX"]
    html = format_audit_html(rebuilt)
    # Before the fix the cached report showed v1 maxima under v2 scores ("14/12")
    assert "14/14" in html and "18/20" in html


def test_report_has_no_emoji_and_embeds_the_brand_font():
    html = format_audit_html(_v2_result())
    assert "✅" not in html and "❌" not in html
    assert '"Stack Sans Headline"' in html and "data:font/woff2;base64," in html
    assert 'class="pill fix"' in html  # the failed Google AI check


def test_report_escapes_the_url():
    html = format_audit_html(AuditResult(url='https://x.test/"><script>alert(1)</script>'))
    assert "<script>alert(1)" not in html


def test_cache_tolerates_unknown_readiness_keys():
    data = _audit_result_to_dict(_v2_result())
    data["google_ai"]["checks"][0]["future_field"] = 1
    data["google_ai"]["checks"].append({"id": "broken"})  # missing required fields: skipped
    assert [c.id for c in _dict_to_audit_result(data).google_ai.checks] == ["G-INDEX"]


def test_google_ai_not_checked_is_not_a_pass():
    result = _v2_result()
    result.google_ai = GoogleAiReadinessResult(checked=False)
    html = format_audit_html(result)
    row = html[html.index("Google AI Search") :]
    assert 'class="pill fix"' in row[: row.index("</tr>")]


def test_pdf_embeds_the_font_and_blocks_local_files(tmp_path):
    try:
        import weasyprint  # noqa: F401

    except (ImportError, OSError) as exc:
        pytest.skip(f"weasyprint or its native C libraries unavailable: {exc}")
    from geo_optimizer.cli.pdf_formatter import _data_only_fetcher, format_audit_pdf

    pdf = format_audit_pdf(_v2_result())
    streams = re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S)
    # decompressobj tolerates a stream the regex cut short (binary data can contain "endstream")
    text = pdf + b"".join(zlib.decompressobj().decompress(s) for s in streams if s[:1] == b"x")
    assert pdf.startswith(b"%PDF") and b"Stack-Sans" in text

    secret = tmp_path / "x.txt"
    secret.write_text("nope")
    fetcher = _data_only_fetcher()
    with pytest.raises(ValueError):
        (fetcher.fetch if hasattr(fetcher, "fetch") else fetcher)(secret.as_uri())
