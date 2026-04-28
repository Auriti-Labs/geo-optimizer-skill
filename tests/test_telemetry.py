"""Test per il modulo Telemetry di GEO Optimizer (v4.10).

Copre:
- Inserzione eventi (5 tipi geo_)
- Validazione event_type
- Recupero con filtri (event_type, domain)
- Eventi di dominio
- Persistenza SQLite
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from geo_optimizer.core.telemetry import (
    _GEO_EVENT_TYPES,
    TELEMETRY_DB_PATH,
    TelemetryStore,
    geo_api_error,
    geo_audit_run,
    geo_badge_generated,
    geo_score_improved,
    geo_suggestion_applied,
)


@pytest.fixture
def store():
    """TelemetryStore con database temporaneo (isolato per test)."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        s = TelemetryStore(Path(tmp.name))
        yield s


class TestTelemetryStore:
    """Test unitari di TelemetryStore."""

    def test_record_audit_run(self, store):
        """record inserisce un geo_audit_run con tutti i campi."""
        store.record(
            "geo_audit_run",
            domain="example.com",
            data={"url": "https://example.com", "score": 75, "band": "good"},
        )
        events = store.get_events(event_type="geo_audit_run")
        assert len(events) == 1
        e = events[0]
        assert e["event_type"] == "geo_audit_run"
        assert e["domain"] == "example.com"
        assert e["data"]["score"] == 75
        assert "recorded_at" in e

    def test_record_all_types(self, store):
        """Tutti i tipi geo_ sono accettati."""
        for et in _GEO_EVENT_TYPES:
            store.record(et, data={"test": et})

        events = store.get_events()
        assert len(events) == len(_GEO_EVENT_TYPES)

    def test_record_rifiuta_event_type_sconosciuto(self, store):
        """record lancia ValueError per evento non valido."""
        with pytest.raises(ValueError) as exc_info:
            store.record("geo_unknown", data={})
        assert "geo_unknown" in str(exc_info.value)
        assert "Expected one of" in str(exc_info.value)

    def test_get_events_domain_filter(self, store):
        """Filtro per domain funziona."""
        store.record("geo_audit_run", domain="a.com", data={})
        store.record("geo_audit_run", domain="b.com", data={})

        events = store.get_events(domain="a.com")
        assert len(events) == 1
        assert events[0]["domain"] == "a.com"

    def test_get_events_limit(self, store):
        """Limit funziona — restituisce massimo N righe."""
        for i in range(100):
            store.record("geo_audit_run", domain="x.com", data={"i": i})

        events = store.get_events(limit=10)
        assert len(events) == 10

    def test_get_events_ordinamento_desc(self, store):
        """Gli eventi sono ordinati per recorded_at DESC."""
        store.record("geo_audit_run", data={"step": 1})
        store.record("geo_audit_run", data={"step": 2})

        events = store.get_events()
        # Il secondo evento (step 2) deve essere il primo nella lista
        assert events[0]["data"]["step"] == 2
        assert events[1]["data"]["step"] == 1

    def test_record_senza_data(self, store):
        """record accetta data=None."""
        store.record("geo_api_error", data=None)
        events = store.get_events()
        assert len(events) == 1
        assert events[0]["data"] == {}


class TestGeoEventEmitters:
    """Test degli helper di emissione eventi (audit_run, score, badge, error, suggestion)."""

    def test_geo_audit_run(self, store):
        """geo_audit_run emette un evento completo."""
        geo_audit_run(
            url="https://example.com/page",
            score=75,
            band="good",
            duration_ms=1234,
            score_breakdown={"robots": 12, "llms": 15},
            store=store,
        )

        events = store.get_events(event_type="geo_audit_run")
        assert len(events) == 1
        d = events[0]["data"]
        assert d["url"] == "https://example.com/page"
        assert d["score"] == 75
        assert d["band"] == "good"
        assert d["duration_ms"] == 1234
        assert d["category"]["robots"] == 12
        assert events[0]["domain"] == "example.com"

    def test_geo_score_improved_solo_se_delta_positivo(self, store):
        """geo_score_improved emette solo se current > previous."""
        geo_score_improved(
            url="https://example.com",
            previous_score=60,
            current_score=75,
            store=store,
        )

        geo_score_improved(
            url="https://example.com",
            previous_score=75,
            current_score=75,  # no change
            store=store,
        )

        geo_score_improved(
            url="https://example.com",
            previous_score=80,
            current_score=70,  # worse
            store=store,
        )

        events = store.get_events(event_type="geo_score_improved")
        assert len(events) == 1
        assert events[0]["data"]["delta"] == 15

    def test_geo_badge_generated(self, store):
        """geo_badge_generated emette payload corretto."""
        geo_badge_generated(
            url="https://example.com",
            score=82,
            band="good",
            store=store,
        )

        events = store.get_events(event_type="geo_badge_generated")
        assert len(events) == 1
        assert events[0]["data"]["score"] == 82

    def test_geo_api_error(self, store):
        """geo_api_error emette evento senza domain (errore generico)."""
        geo_api_error(
            endpoint="/api/audit",
            error="Timeout",
            status_code=504,
            store=store,
        )

        events = store.get_events(event_type="geo_api_error")
        assert len(events) == 1
        d = events[0]["data"]
        assert d["endpoint"] == "/api/audit"
        assert d["status_code"] == 504
        assert events[0]["domain"] == ""

    def test_geo_suggestion_applied(self, store):
        """geo_suggestion_applied emette evento con suggestion."""
        geo_suggestion_applied(
            suggestion="Add canonical tag",
            url="https://example.com",
            store=store,
        )

        events = store.get_events(event_type="geo_suggestion_applied")
        assert len(events) == 1
        assert events[0]["data"]["suggestion"] == "Add canonical tag"
        assert events[0]["domain"] == "example.com"

    def test_geo_suggestion_applied_senza_url(self, store):
        """geo_suggestion_applied funziona anche senza URL."""
        geo_suggestion_applied(
            suggestion="Add canonical tag",
            store=store,
        )

        events = store.get_events(event_type="geo_suggestion_applied")
        assert len(events) == 1
        assert events[0]["domain"] == ""


class TestTelemetryDbPath:
    """Test path e persistenza."""

    def test_telemetry_db_path_in_geo_optimizer_home(self):
        """TELEMETRY_DB_PATH è dentro ~/.geo-optimizer."""
        assert "telemetry.db" in str(TELEMETRY_DB_PATH)
        assert ".geo-optimizer" in str(TELEMETRY_DB_PATH)

    def test_db_creato_automaticamente(self, store):
        """Il file DB esiste dopo l'uso."""
        store.record("geo_audit_run", data={})
        assert store.db_path.exists()

    def test_events_persistono_fra_istanze(self, store):
        """Dati persistenti su disco — nuova istanza vede vecchi eventi."""
        store.record("geo_audit_run", data={"url": "a"})

        store2 = TelemetryStore(store.db_path)
        events = store2.get_events()
        assert len(events) == 1
