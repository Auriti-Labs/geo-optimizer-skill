"""Archivio locale di snapshot completi delle risposte AI."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from geo_optimizer.models.config import DEFAULT_SNAPSHOT_LIMIT, SNAPSHOTS_DB_PATH
from geo_optimizer.models.results import AnswerCitation, AnswerSnapshot, AnswerSnapshotArchive

_URL_RE = re.compile(r"https?://[^\s<>\"]+")


def _normalize_timestamp(value: str | None) -> str:
    """Normalizza un timestamp in ISO 8601."""
    if not value:
        return datetime.now(timezone.utc).isoformat()

    candidate = value.strip()
    if len(candidate) == 10:
        return f"{candidate}T00:00:00+00:00"
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return candidate
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def _normalize_filter_date(value: str | None, end_of_day: bool = False) -> str | None:
    """Converte filtri data semplici in timestamp ISO confrontabili."""
    if not value:
        return None
    raw = value.strip()
    if len(raw) == 10:
        suffix = "T23:59:59+00:00" if end_of_day else "T00:00:00+00:00"
        return f"{raw}{suffix}"
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return raw


def _citation_from_url(url: str, position: int) -> AnswerCitation:
    """Crea una citazione normalizzata da una URL."""
    cleaned = url.rstrip(").,;]")
    parsed = urlparse(cleaned)
    return AnswerCitation(
        url=cleaned,
        position=position,
        domain=(parsed.hostname or "").lower(),
    )


def extract_citations(answer_text: str, extra_urls: list[str] | None = None) -> list[AnswerCitation]:
    """Estrae URL citate dal testo e aggiunge eventuali URL extra deduplicate."""
    citations: list[AnswerCitation] = []
    seen: set[str] = set()

    for index, match in enumerate(_URL_RE.finditer(answer_text), start=1):
        citation = _citation_from_url(match.group(0), index)
        if citation.url in seen:
            continue
        seen.add(citation.url)
        citations.append(citation)

    for url in extra_urls or []:
        citation = _citation_from_url(url, len(citations) + 1)
        if citation.url in seen:
            continue
        seen.add(citation.url)
        citations.append(citation)

    return citations


class SnapshotStore:
    """Storage SQLite locale per snapshot completi di risposte AI."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or SNAPSHOTS_DB_PATH
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
                CREATE TABLE IF NOT EXISTS answer_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_text TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS answer_snapshot_citations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    citation_url TEXT NOT NULL,
                    citation_domain TEXT NOT NULL,
                    citation_position INTEGER NOT NULL,
                    FOREIGN KEY (snapshot_id) REFERENCES answer_snapshots(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_answer_snapshots_query_time
                ON answer_snapshots (query_text, recorded_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_answer_snapshot_citations_snapshot
                ON answer_snapshot_citations (snapshot_id, citation_position ASC)
                """
            )

    def save_snapshot(
        self,
        query: str,
        prompt: str,
        answer_text: str,
        model: str,
        provider: str = "",
        recorded_at: str | None = None,
        citation_urls: list[str] | None = None,
    ) -> AnswerSnapshot:
        """Salva uno snapshot completo con citazioni estratte o passate esplicitamente."""
        timestamp = _normalize_timestamp(recorded_at)
        citations = extract_citations(answer_text, extra_urls=citation_urls)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO answer_snapshots (
                    query_text,
                    prompt_text,
                    model_name,
                    provider_name,
                    answer_text,
                    recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (query, prompt, model, provider, answer_text, timestamp),
            )
            snapshot_id = int(cursor.lastrowid or 0)
            for citation in citations:
                conn.execute(
                    """
                    INSERT INTO answer_snapshot_citations (
                        snapshot_id,
                        citation_url,
                        citation_domain,
                        citation_position
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (snapshot_id, citation.url, citation.domain, int(citation.position)),
                )

        return AnswerSnapshot(
            snapshot_id=snapshot_id,
            query=query,
            prompt=prompt,
            model=model,
            provider=provider,
            answer_text=answer_text,
            recorded_at=timestamp,
            citations=citations,
        )

    def get_snapshot(self, snapshot_id: int) -> AnswerSnapshot | None:
        """Recupera uno snapshot singolo con le relative citazioni."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM answer_snapshots WHERE id = ?",
                (int(snapshot_id),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_snapshot(conn, row)

    def list_snapshots(
        self,
        query: str = "",
        date_from: str | None = None,
        date_to: str | None = None,
        model: str = "",
        limit: int = DEFAULT_SNAPSHOT_LIMIT,
    ) -> AnswerSnapshotArchive:
        """Restituisce gli snapshot filtrati per query, date e modello."""
        conditions: list[str] = []
        params: list[object] = []

        if query:
            conditions.append("query_text = ?")
            params.append(query)
        if model:
            conditions.append("model_name = ?")
            params.append(model)
        if date_from:
            conditions.append("recorded_at >= ?")
            params.append(_normalize_filter_date(date_from, end_of_day=False))
        if date_to:
            conditions.append("recorded_at <= ?")
            params.append(_normalize_filter_date(date_to, end_of_day=True))

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query_sql = f"SELECT * FROM answer_snapshots {where_clause} ORDER BY recorded_at DESC, id DESC LIMIT ?"
        count_sql = f"SELECT COUNT(*) FROM answer_snapshots {where_clause}"

        with self._connect() as conn:
            rows = conn.execute(query_sql, (*params, limit)).fetchall()
            total = int(conn.execute(count_sql, params).fetchone()[0])

            entries = [self._row_to_snapshot(conn, row) for row in rows]

        return AnswerSnapshotArchive(
            query=query,
            date_from=date_from,
            date_to=date_to,
            total_snapshots=total,
            entries=entries,
        )

    def _row_to_snapshot(self, conn: sqlite3.Connection, row: sqlite3.Row) -> AnswerSnapshot:
        """Converte una riga SQLite in snapshot completo con citazioni."""
        citation_rows = conn.execute(
            """
            SELECT citation_url, citation_domain, citation_position
            FROM answer_snapshot_citations
            WHERE snapshot_id = ?
            ORDER BY citation_position ASC, id ASC
            """,
            (int(row["id"]),),
        ).fetchall()
        citations = [
            AnswerCitation(
                url=citation_row["citation_url"],
                domain=citation_row["citation_domain"],
                position=int(citation_row["citation_position"]),
            )
            for citation_row in citation_rows
        ]
        return AnswerSnapshot(
            snapshot_id=int(row["id"]),
            query=row["query_text"],
            prompt=row["prompt_text"],
            model=row["model_name"],
            provider=row["provider_name"],
            answer_text=row["answer_text"],
            recorded_at=row["recorded_at"],
            citations=citations,
        )
