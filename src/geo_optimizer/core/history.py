"""Persistenza locale della history GEO e trend tracking."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from geo_optimizer.models.config import (
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_HISTORY_RETENTION_DAYS,
    TRACKING_DB_PATH,
)
from geo_optimizer.models.results import AuditResult, HistoryEntry, HistoryResult

_CATEGORY_KEYS = (
    "robots",
    "llms",
    "schema",
    "meta",
    "content",
    "signals",
    "ai_discovery",
    "brand_entity",
)


def canonicalize_history_url(url: str) -> str:
    """Normalizza una URL per l'uso nella history locale."""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return f"{scheme}://{host}{path}"


def summarize_history(result: HistoryResult) -> dict[str, object]:
    """Restituisce una sintesi serializzabile della history."""
    return {
        "retention_days": result.retention_days,
        "total_snapshots": result.total_snapshots,
        "latest_score": result.latest_score,
        "latest_band": result.latest_band,
        "previous_score": result.previous_score,
        "score_delta": result.score_delta,
        "regression_detected": result.regression_detected,
        "best_score": result.best_score,
        "worst_score": result.worst_score,
        "entries": [
            {
                "timestamp": entry.timestamp,
                "score": entry.score,
                "band": entry.band,
                "delta": entry.delta,
            }
            for entry in result.entries
        ],
    }


class HistoryStore:
    """Storage SQLite locale per snapshot GEO e trend analysis."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or TRACKING_DB_PATH
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
                CREATE TABLE IF NOT EXISTS audit_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_url TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    band TEXT NOT NULL,
                    http_status INTEGER NOT NULL,
                    recommendations_count INTEGER NOT NULL,
                    robots_score INTEGER NOT NULL,
                    llms_score INTEGER NOT NULL,
                    schema_score INTEGER NOT NULL,
                    meta_score INTEGER NOT NULL,
                    content_score INTEGER NOT NULL,
                    signals_score INTEGER NOT NULL,
                    ai_discovery_score INTEGER NOT NULL,
                    brand_entity_score INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_history_url_time
                ON audit_history (canonical_url, recorded_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_history_domain_time
                ON audit_history (domain, recorded_at DESC)
                """
            )
            # Migrazione additiva: gli snapshot pre-rubric v2 restano versione 1
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(audit_history)")}
            if "score_version" not in columns:
                try:
                    conn.execute("ALTER TABLE audit_history ADD COLUMN score_version INTEGER NOT NULL DEFAULT 1")
                except sqlite3.OperationalError as exc:
                    # Un altro processo ha migrato nel frattempo: la colonna c'è, va bene così
                    if "duplicate column" not in str(exc).lower():
                        raise

    def prune_old_entries(self, retention_days: int = DEFAULT_HISTORY_RETENTION_DAYS) -> int:
        """Rimuove gli snapshot più vecchi della retention configurata."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM audit_history
                WHERE julianday('now') - julianday(recorded_at) > ?
                """,
                (retention_days,),
            )
            return int(cursor.rowcount or 0)

    def get_latest_entry(self, url: str) -> HistoryEntry | None:
        """Recupera l'ultimo snapshot salvato per una URL."""
        canonical_url = canonicalize_history_url(url)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM audit_history
                WHERE canonical_url = ?
                ORDER BY recorded_at DESC, id DESC
                LIMIT 1
                """,
                (canonical_url,),
            ).fetchone()
        return self._row_to_entry(row) if row else None

    def save_audit_result(
        self,
        result: AuditResult,
        retention_days: int = DEFAULT_HISTORY_RETENTION_DAYS,
    ) -> HistoryEntry:
        """Salva uno snapshot di audit e restituisce l'entry persistita."""
        previous = self.get_latest_entry(result.url)
        canonical_url = canonicalize_history_url(result.url)
        parsed = urlparse(canonical_url)
        domain = parsed.hostname or ""
        breakdown = {key: int(result.score_breakdown.get(key, 0)) for key in _CATEGORY_KEYS}

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_history (
                    canonical_url,
                    domain,
                    recorded_at,
                    score,
                    band,
                    http_status,
                    recommendations_count,
                    robots_score,
                    llms_score,
                    schema_score,
                    meta_score,
                    content_score,
                    signals_score,
                    ai_discovery_score,
                    brand_entity_score,
                    score_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    canonical_url,
                    domain,
                    result.timestamp,
                    int(result.score),
                    result.band,
                    int(result.http_status),
                    len(result.recommendations),
                    breakdown["robots"],
                    breakdown["llms"],
                    breakdown["schema"],
                    breakdown["meta"],
                    breakdown["content"],
                    breakdown["signals"],
                    breakdown["ai_discovery"],
                    breakdown["brand_entity"],
                    int(result.score_version),
                ),
            )

        self.prune_old_entries(retention_days=retention_days)

        comparable = previous is not None and previous.score_version == result.score_version
        delta = int(result.score) - previous.score if comparable else None
        return HistoryEntry(
            url=canonical_url,
            timestamp=result.timestamp,
            score=int(result.score),
            band=result.band,
            http_status=int(result.http_status),
            recommendations_count=len(result.recommendations),
            score_breakdown=breakdown,
            delta=delta,
            score_version=int(result.score_version),
        )

    def build_history_result(
        self,
        url: str,
        limit: int = DEFAULT_HISTORY_LIMIT,
        retention_days: int = DEFAULT_HISTORY_RETENTION_DAYS,
    ) -> HistoryResult:
        """Costruisce il trend storico per una URL."""
        self.prune_old_entries(retention_days=retention_days)
        canonical_url = canonicalize_history_url(url)

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM audit_history
                WHERE canonical_url = ?
                ORDER BY recorded_at DESC, id DESC
                LIMIT ?
                """,
                (canonical_url, limit),
            ).fetchall()
            total_snapshots = conn.execute(
                "SELECT COUNT(*) FROM audit_history WHERE canonical_url = ?",
                (canonical_url,),
            ).fetchone()[0]

        entries = [self._row_to_entry(row) for row in rows]
        for index, entry in enumerate(entries):
            previous = entries[index + 1] if index + 1 < len(entries) else None
            # Score di rubric diverse non sono confrontabili: nessun delta, nessuna regressione fittizia
            same = previous is not None and previous.score_version == entry.score_version
            entry.delta = entry.score - previous.score if same else None

        latest = entries[0] if entries else None
        previous = entries[1] if len(entries) > 1 else None
        if latest and previous and latest.score_version != previous.score_version:
            previous = None

        return HistoryResult(
            url=canonical_url,
            retention_days=retention_days,
            total_snapshots=int(total_snapshots),
            latest_score=latest.score if latest else None,
            latest_band=latest.band if latest else None,
            previous_score=previous.score if previous else None,
            score_delta=(latest.score - previous.score) if latest and previous else None,
            regression_detected=bool(latest and previous and latest.score < previous.score),
            best_score=max((entry.score for entry in entries), default=None),
            worst_score=min((entry.score for entry in entries), default=None),
            entries=entries,
        )

    def _row_to_entry(self, row: sqlite3.Row) -> HistoryEntry:
        """Converte una riga SQLite in HistoryEntry."""
        breakdown = {
            "robots": int(row["robots_score"]),
            "llms": int(row["llms_score"]),
            "schema": int(row["schema_score"]),
            "meta": int(row["meta_score"]),
            "content": int(row["content_score"]),
            "signals": int(row["signals_score"]),
            "ai_discovery": int(row["ai_discovery_score"]),
            "brand_entity": int(row["brand_entity_score"]),
        }
        return HistoryEntry(
            url=row["canonical_url"],
            timestamp=row["recorded_at"],
            score=int(row["score"]),
            band=row["band"],
            http_status=int(row["http_status"]),
            recommendations_count=int(row["recommendations_count"]),
            score_breakdown=breakdown,
            score_version=int(row["score_version"]),
        )
