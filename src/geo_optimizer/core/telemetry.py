"""Telemetry tracking for GEO Optimizer web demo.

Tracks structured events with geo_ prefix for usage analytics.
Events stored in SQLite (TRACKING_DB_PATH by default).

Events:
- geo_audit_run: audit completed (url, score, band, duration_ms)
- geo_score_improved: score delta > 0 vs previous audit (delta)
- geo_suggestion_applied: fix suggestion accepted
- geo_api_error: API endpoint failure (endpoint, error, status_code)
- geo_badge_generated: badge SVG served (url, score, band)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from geo_optimizer.models.config import GEO_OPTIMIZER_HOME

TELEMETRY_DB_PATH: Path = GEO_OPTIMIZER_HOME / "telemetry.db"

_GEO_EVENT_TYPES: frozenset[str] = frozenset({
    "geo_audit_run",
    "geo_score_improved",
    "geo_suggestion_applied",
    "geo_api_error",
    "geo_badge_generated",
})


class TelemetryStore:
    """SQLite-backed event store for GEO telemetry."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or TELEMETRY_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS geo_events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type  TEXT    NOT NULL,
                    recorded_at TEXT    NOT NULL,
                    domain      TEXT,
                    data        TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_geo_events_type_time
                ON geo_events (event_type, recorded_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_geo_events_domain_time
                ON geo_events (domain, recorded_at DESC)
                """
            )

    def record(
        self,
        event_type: str,
        *,
        domain: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        """Record a GEO event.

        Args:
            event_type: must be in _GEO_EVENT_TYPES.
            domain: optional domain for filtering.
            data: serializable dict with event payload.

        Raises:
            ValueError: if event_type is not a valid GEO event.
        """
        if event_type not in _GEO_EVENT_TYPES:
            raise ValueError(
                f"Unknown event type: {event_type}. "
                f"Expected one of: {sorted(_GEO_EVENT_TYPES)}"
            )

        recorded_at = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(data or {})

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO geo_events (event_type, recorded_at, domain, data)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, recorded_at, domain, data_json),
            )

    def get_latest_audit_score(self, url: str) -> int | None:
        """Ritorna lo score dell'ultimo geo_audit_run per una URL, o None se assente.

        Utility per calcolare il delta di geo_score_improved senza dipendere
        da HistoryStore.
        """
        domain = ""
        try:
            from urllib.parse import urlparse as _urlparse

            domain = _urlparse(url).hostname or ""
        except Exception:
            pass

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT data
                FROM geo_events
                WHERE event_type = 'geo_audit_run'
                  AND (domain = ? OR data LIKE ?)
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (domain, f'%"url": "{url}"%'),
            ).fetchone()

        if row is None:
            return None
        data = json.loads(row["data"]) if row["data"] else {}
        return data.get("score")

    def get_events(
        self,
        event_type: str | None = None,
        domain: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve events with optional filtering.

        Args:
            event_type: filter by event type.
            domain: filter by domain.
            limit: max rows to return.

        Returns:
            List of event dicts (id, event_type, recorded_at, domain, data).
        """
        query_parts = ["SELECT * FROM geo_events WHERE 1=1"]
        params: list[Any] = []

        if event_type:
            query_parts.append("AND event_type = ?")
            params.append(event_type)
        if domain:
            query_parts.append("AND domain = ?")
            params.append(domain)

        query_parts.append("ORDER BY recorded_at DESC LIMIT ?")
        params.append(limit)

        query = " ".join(query_parts)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "recorded_at": row["recorded_at"],
                    "domain": row["domain"],
                    "data": json.loads(row["data"]) if row["data"] else {},
                }
                for row in rows
            ]


# ── Event emitters ──────────────────────────────────────────────────────────

# v4.10: singleton TelemetryStore (lazy init)
_default_telemetry_store: TelemetryStore | None = None


def _telemetry() -> TelemetryStore:
    """Factory: ritorna l'istanza singleton di TelemetryStore."""
    global _default_telemetry_store
    if _default_telemetry_store is None:
        _default_telemetry_store = TelemetryStore()
    return _default_telemetry_store


def geo_audit_run(
    *,
    url: str,
    score: int,
    band: str,
    duration_ms: int,
    score_breakdown: dict[str, int] | None = None,
    store: TelemetryStore | None = None,
) -> None:
    """Emit geo_audit_run event after audit completion."""
    from urllib.parse import urlparse

    domain = urlparse(url).hostname or ""
    (store or _telemetry()).record(
        "geo_audit_run",
        domain=domain,
        data={
            "url": url,
            "score": score,
            "band": band,
            "duration_ms": duration_ms,
            "category": score_breakdown or {},
        },
    )


def geo_score_improved(
    *,
    url: str,
    previous_score: int,
    current_score: int,
    store: TelemetryStore | None = None,
) -> None:
    """Emit geo_score_improved when score increases vs previous audit."""
    from urllib.parse import urlparse

    if current_score <= previous_score:
        return

    domain = urlparse(url).hostname or ""
    delta = current_score - previous_score
    (store or _telemetry()).record(
        "geo_score_improved",
        domain=domain,
        data={
            "url": url,
            "previous_score": previous_score,
            "current_score": current_score,
            "delta": delta,
        },
    )


def geo_suggestion_applied(
    *,
    suggestion: str,
    url: str = "",
    store: TelemetryStore | None = None,
) -> None:
    """Emit geo_suggestion_applied when a fix suggestion is accepted."""
    from urllib.parse import urlparse

    domain = urlparse(url).hostname or "" if url else ""
    (store or _telemetry()).record(
        "geo_suggestion_applied",
        domain=domain,
        data={"suggestion": suggestion, "url": url},
    )


def geo_api_error(
    *,
    endpoint: str,
    error: str,
    status_code: int = 0,
    store: TelemetryStore | None = None,
) -> None:
    """Emit geo_api_error when an API endpoint fails."""
    (store or _telemetry()).record(
        "geo_api_error",
        data={
            "endpoint": endpoint,
            "error": error,
            "status_code": status_code,
        },
    )


def geo_badge_generated(
    *,
    url: str,
    score: int,
    band: str,
    store: TelemetryStore | None = None,
) -> None:
    """Emit geo_badge_generated when a badge SVG is served."""
    from urllib.parse import urlparse

    domain = urlparse(url).hostname or ""
    (store or _telemetry()).record(
        "geo_badge_generated",
        domain=domain,
        data={"url": url, "score": score, "band": band},
    )
