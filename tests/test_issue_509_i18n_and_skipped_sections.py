"""Issue #509 — no Italian in the English report, and no silent section gaps.

Two defects reported together by a user running 4.15.0 on Windows:
  * section 8 printed four Italian strings inside an otherwise English report;
  * the numbering jumped 13 -> 15, which reads as a bug.

The second one was not a bug in the section: EMBEDDING PROXIMITY is conditional on
the optional sentence-transformers extra. The bug was that the formatter recorded
why it skipped and then never said so.
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src/geo_optimizer/cli"

# Italian words that leaked. Matched as whole words so English text that merely
# contains these letter sequences does not trip the test.
_ITALIAN = (
    "coerente",
    "incoerente",
    "presenti",
    "mancanti",
    "trovate",
    "trovati",
    "collegata",
    "rilevata",
    "Nessuno",
    "Nessun",
    "Articoli",
    "Informazioni",
)


def _user_facing_strings(path: Path) -> list[str]:
    """String literals from the file, minus comments and docstrings."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*#.*$", "", text, flags=re.MULTILINE)
    return re.findall(r'"([^"\n]{4,})"', text)


class TestNoItalianLeak:
    def test_text_formatter_is_english(self):
        offenders = [
            s for s in _user_facing_strings(_SRC / "formatters.py") if any(re.search(rf"\b{w}\b", s) for w in _ITALIAN)
        ]
        assert not offenders, f"Italian strings still in the text formatter: {offenders}"

    def test_rich_formatter_is_english(self):
        offenders = [
            s
            for s in _user_facing_strings(_SRC / "rich_formatter.py")
            if any(re.search(rf"\b{w}\b", s) for w in _ITALIAN)
        ]
        assert not offenders, f"Italian strings still in the rich formatter: {offenders}"

    def test_the_exact_strings_from_the_report_are_gone(self):
        """The four lines the reporter pasted, verbatim."""
        blob = (_SRC / "formatters.py").read_text(encoding="utf-8")
        for reported in (
            "Brand name coerente",
            "About page collegata",
            "Informazioni di contatto presenti",
            "Knowledge Graph pillars",  # this one stays: it is English
        ):
            if reported == "Knowledge Graph pillars":
                assert reported in blob, "the English label was removed by mistake"
            else:
                assert reported not in blob, f"still present: {reported}"


class TestSkippedSectionIsExplained:
    """A conditional section must say it was skipped, not vanish."""

    def _render(self, *, skipped: str | None):
        """Render a real AuditResult, reusing the fixture helper the suite already
        has. A hand-rolled stand-in silently diverges from the dataclass and turns a
        formatter change into an unrelated AttributeError."""
        from geo_optimizer.cli.formatters import format_audit_text
        from geo_optimizer.models.results import EmbeddingProximityResult
        from tests.test_v21_coverage import _make_audit_result

        ep = EmbeddingProximityResult(
            checked=True,
            skipped_reason=skipped,
            model_name="all-MiniLM-L6-v2",
            avg_similarity=0.42,
            top_similarity=0.81,
            retrievable_chunks=3,
            total_chunks=7,
        )
        result = _make_audit_result()
        result.embedding_proximity = ep
        return format_audit_text(result)

    def test_skipped_section_states_the_reason(self):
        out = self._render(skipped="sentence-transformers not installed (pip install geo-optimizer-skill[embedding])")
        assert "14. EMBEDDING PROXIMITY" in out, "the section header must still appear"
        assert "Skipped" in out
        assert "sentence-transformers" in out, "the actionable reason must reach the user"

    def test_numbering_has_no_hole_when_skipped(self):
        """The reporter's actual symptom: 13 followed by 15."""
        out = self._render(skipped="sentence-transformers not installed")
        assert "14." in out

    def test_completed_section_still_prints_the_metrics(self):
        out = self._render(skipped=None)
        assert "Model: all-MiniLM-L6-v2" in out
        assert "Skipped" not in out
