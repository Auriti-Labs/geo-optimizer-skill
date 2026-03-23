"""
Local HTTP cache on filesystem.

Saves HTTP responses in ``~/.geo-cache/`` to avoid repeated fetches
during development. Disabled by default, enabled with ``--cache``.

Usage:
    geo audit --url https://example.com --cache
    geo audit --url https://example.com --clear-cache
"""

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Optional

# Cache directory in the user's home
CACHE_DIR = Path.home() / ".geo-cache"

# Default TTL: 1 hour
DEFAULT_TTL = 3600

# Disk cache size limit: 500 MB (fix #192)
MAX_CACHE_SIZE_BYTES = 500 * 1024 * 1024


class FileCache:
    """HTTP cache on filesystem with TTL."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl: int = DEFAULT_TTL):
        self.cache_dir = cache_dir or CACHE_DIR
        self.ttl = ttl

    def _key(self, url: str) -> str:
        """Generate cache key from URL (SHA-256 hash)."""
        return hashlib.sha256(url.encode()).hexdigest()

    def _path(self, url: str) -> Path:
        """Cache file path for a URL."""
        return self.cache_dir / f"{self._key(url)}.json"

    def get(self, url: str) -> Optional[tuple[int, str, dict]]:
        """Retrieve response from cache if valid.

        Returns:
            Tuple (status_code, text, headers) or None if not cached/expired.
        """
        path = self._path(url)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Check TTL
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
        """Salva risposta nella cache. Evicts oldest if over disk limit (fix #192)."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Evict oldest entries if cache exceeds disk limit
        self._evict_if_needed()

        data = {
            "url": url,
            "status_code": status_code,
            "text": text,
            "headers": dict(headers),
            "cached_at": time.time(),
        }

        path = self._path(url)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _evict_if_needed(self) -> None:
        """Remove oldest cache entries if total size exceeds MAX_CACHE_SIZE_BYTES."""
        if not self.cache_dir.exists():
            return

        files = sorted(self.cache_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
        total_size = sum(f.stat().st_size for f in files)

        while total_size > MAX_CACHE_SIZE_BYTES and files:
            oldest = files.pop(0)
            try:
                total_size -= oldest.stat().st_size
                oldest.unlink(missing_ok=True)
            except FileNotFoundError:
                pass  # Already removed by another thread (fix #195)

    def clear(self) -> int:
        """Clear the entire cache. Returns the number of files removed."""
        if not self.cache_dir.exists():
            return 0

        count = sum(1 for _ in self.cache_dir.glob("*.json"))
        shutil.rmtree(self.cache_dir)
        return count

    def stats(self) -> dict:
        """Cache statistics: file count, total size."""
        if not self.cache_dir.exists():
            return {"files": 0, "size_bytes": 0}

        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        return {"files": len(files), "size_bytes": total_size}
