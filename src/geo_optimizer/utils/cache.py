"""
Cache HTTP locale su filesystem.

Salva le risposte HTTP in ``~/.geo-cache/`` per evitare fetch ripetuti
durante lo sviluppo. Disabilitata di default, attivabile con ``--cache``.

Uso:
    geo audit --url https://example.com --cache
    geo audit --url https://example.com --clear-cache
"""

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Optional

# Directory cache nella home dell'utente
CACHE_DIR = Path.home() / ".geo-cache"

# TTL di default: 1 ora
DEFAULT_TTL = 3600


class FileCache:
    """Cache HTTP su filesystem con TTL."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl: int = DEFAULT_TTL):
        self.cache_dir = cache_dir or CACHE_DIR
        self.ttl = ttl

    def _key(self, url: str) -> str:
        """Genera chiave cache da URL (hash SHA-256)."""
        return hashlib.sha256(url.encode()).hexdigest()

    def _path(self, url: str) -> Path:
        """Percorso file cache per un URL."""
        return self.cache_dir / f"{self._key(url)}.json"

    def get(self, url: str) -> Optional[tuple[int, str, dict]]:
        """Recupera risposta dalla cache se valida.

        Returns:
            Tupla (status_code, text, headers) o None se non in cache/scaduta.
        """
        path = self._path(url)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Verifica TTL
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > self.ttl:
            path.unlink(missing_ok=True)
            return None

        return (
            data.get("status_code", 200),
            data.get("text", ""),
            data.get("headers", {}),
        )

    def put(self, url: str, status_code: int, text: str, headers: dict) -> None:
        """Salva risposta nella cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "url": url,
            "status_code": status_code,
            "text": text,
            "headers": dict(headers),
            "cached_at": time.time(),
        }

        path = self._path(url)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def clear(self) -> int:
        """Svuota tutta la cache. Ritorna il numero di file rimossi."""
        if not self.cache_dir.exists():
            return 0

        count = sum(1 for _ in self.cache_dir.glob("*.json"))
        shutil.rmtree(self.cache_dir)
        return count

    def stats(self) -> dict:
        """Statistiche cache: numero file, dimensione totale."""
        if not self.cache_dir.exists():
            return {"files": 0, "size_bytes": 0}

        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        return {"files": len(files), "size_bytes": total_size}
