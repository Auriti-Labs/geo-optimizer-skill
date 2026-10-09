"""La skill documenta ogni check Google AI e i pesi della rubric v2."""

from __future__ import annotations

from pathlib import Path

from geo_optimizer.models.config import CATEGORY_MAX_V2, GOOGLE_AI_POINTS

ROOT = Path(__file__).resolve().parent.parent


def _skill_text() -> str:
    parts = [ROOT / "SKILL.md", *sorted((ROOT / "src/geo_optimizer/skills/catalog").rglob("prompt.md"))]
    return "\n".join(p.read_text(encoding="utf-8") for p in parts)


def test_every_google_check_id_is_documented_in_the_skill():
    text = _skill_text()
    missing = [cid for cid in GOOGLE_AI_POINTS if cid not in text]
    assert not missing, f"skill missing check IDs: {missing}"


def test_skill_states_v2_category_weights():
    text = _skill_text()
    assert "Google AI readiness" in text and "score_version" in text
    missing = [key for key in CATEGORY_MAX_V2 if f"`{key}`" not in text]
    assert not missing, f"skill missing v2 categories: {missing}"
    assert f"| {CATEGORY_MAX_V2['llms']} |" in text
