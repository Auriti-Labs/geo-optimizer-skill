"""Test per l'archivio locale degli answer snapshot AI."""

from __future__ import annotations

from pathlib import Path

from geo_optimizer.core.snapshots import SnapshotStore, extract_citations


def test_extract_citations_deduplica_e_preserva_posizione():
    """Le URL nel testo vengono estratte una sola volta con posizione stabile."""
    text = (
        "Use https://example.com/page and https://example.com/page for details. "
        "Compare also https://other.example.org/report."
    )

    citations = extract_citations(text)

    assert len(citations) == 2
    assert citations[0].url == "https://example.com/page"
    assert citations[0].position == 1
    assert citations[1].domain == "other.example.org"


def test_snapshot_store_save_and_list_filters(tmp_path):
    """Gli snapshot salvati sono interrogabili per query e range temporale."""
    store = SnapshotStore(Path(tmp_path / "snapshots.db"))
    first = store.save_snapshot(
        query="best GEO tool",
        prompt="What is the best GEO tool?",
        answer_text="GEO Optimizer is cited at https://example.com and https://docs.example.com.",
        model="gpt-5.4",
        provider="openai",
        recorded_at="2026-03-10",
    )
    second = store.save_snapshot(
        query="best GEO tool",
        prompt="What is the best GEO tool?",
        answer_text="Another answer citing https://competitor.example.com.",
        model="gpt-5.4",
        provider="openai",
        recorded_at="2026-03-20",
    )
    store.save_snapshot(
        query="ai visibility tools",
        prompt="Which AI visibility tools exist?",
        answer_text="Mentions https://third.example.net",
        model="claude-4",
        provider="anthropic",
        recorded_at="2026-04-01",
    )

    archive = store.list_snapshots(query="best GEO tool", date_from="2026-03-15", date_to="2026-03-31")

    assert first.snapshot_id > 0
    assert second.snapshot_id > first.snapshot_id
    assert len(first.citations) == 2
    assert archive.total_snapshots == 1
    assert len(archive.entries) == 1
    assert archive.entries[0].recorded_at.startswith("2026-03-20")
    assert archive.entries[0].citations[0].domain == "competitor.example.com"
