"""Test per il quality scoring delle citazioni archiviate."""

from __future__ import annotations

from geo_optimizer.core.citation_quality import analyze_snapshot_citation_quality
from geo_optimizer.models.results import AnswerCitation, AnswerSnapshot


def test_analyze_snapshot_citation_quality_assegna_tier_e_position_score():
    """Le citazioni vengono classificate per tier e posizione."""
    snapshot = AnswerSnapshot(
        snapshot_id=7,
        query="best GEO tool",
        model="gpt-5.4",
        provider="openai",
        answer_text=(
            "We recommend GEO Optimizer for teams that need fast audits: https://example.com/report. "
            "Tools like Rival Suite can also help: https://rival.example.com/tool. "
            "Some tools exist, such as https://other.example.net/app."
        ),
        citations=[
            AnswerCitation(url="https://example.com/report", domain="example.com", position=1),
            AnswerCitation(url="https://rival.example.com/tool", domain="rival.example.com", position=2),
            AnswerCitation(url="https://other.example.net/app", domain="other.example.net", position=3),
        ],
    )

    report = analyze_snapshot_citation_quality(snapshot)

    assert report.total_citations == 3
    assert report.analyzed_citations == 3
    assert report.entries[0].domain == "example.com"
    assert report.entries[0].tier == 1
    assert report.entries[0].position_score == 5
    assert report.entries[1].tier == 3
    assert report.entries[2].tier == 4


def test_analyze_snapshot_citation_quality_filtra_target_domain():
    """Il filtro target_domain limita l'analisi alle citazioni richieste."""
    snapshot = AnswerSnapshot(
        snapshot_id=8,
        query="best GEO tool",
        model="claude-4",
        answer_text="We recommend https://example.com/report and compare it with https://other.example.net/app.",
        citations=[
            AnswerCitation(url="https://example.com/report", domain="example.com", position=1),
            AnswerCitation(url="https://other.example.net/app", domain="other.example.net", position=2),
        ],
    )

    report = analyze_snapshot_citation_quality(snapshot, target_domain="example.com")

    assert report.analyzed_citations == 1
    assert report.entries[0].domain == "example.com"
