"""
Client HTTP asincrono con httpx per fetch parallelo.

Velocizza l'audit eseguendo robots.txt, llms.txt e homepage in parallelo
(speedup 2-3x rispetto al fetch sequenziale con requests).

Richiede httpx come dipendenza opzionale:
    pip install geo-optimizer-skill[async]
"""

import asyncio
from typing import Optional, Tuple

from geo_optimizer.models.config import HEADERS
from geo_optimizer.utils.http import MAX_RESPONSE_SIZE


def is_httpx_available() -> bool:
    """Verifica se httpx è installato."""
    try:
        import httpx  # noqa: F401

        return True
    except ImportError:
        return False


async def fetch_url_async(
    url: str,
    client=None,
    timeout: int = 10,
    max_size: int = MAX_RESPONSE_SIZE,
) -> Tuple[Optional[object], Optional[str]]:
    """Fetch asincrono di un URL con httpx.

    Args:
        url: URL da scaricare.
        client: httpx.AsyncClient opzionale (riutilizza connessioni).
        timeout: Timeout in secondi.
        max_size: Dimensione massima risposta in bytes.

    Returns:
        Tupla (response, error_msg) — response è None in caso di errore.
    """
    import httpx

    own_client = client is None

    try:
        if own_client:
            client = httpx.AsyncClient(
                headers=HEADERS,
                follow_redirects=True,
                timeout=httpx.Timeout(timeout),
            )

        r = await client.get(url)

        # Verifica Content-Length se disponibile
        content_length = r.headers.get("content-length")
        if content_length and int(content_length) > max_size:
            return None, f"Response too large: {int(content_length)} bytes (max: {max_size})"

        # Verifica dimensione effettiva
        if len(r.content) > max_size:
            return None, f"Response too large: {len(r.content)} bytes (max: {max_size})"

        return r, None

    except httpx.TimeoutException:
        return None, f"Timeout ({timeout}s)"
    except httpx.ConnectError as e:
        return None, f"Connection failed: {e}"
    except Exception as e:
        return None, str(e)
    finally:
        if own_client and client:
            await client.aclose()


async def fetch_urls_async(
    urls: list,
    timeout: int = 10,
    max_size: int = MAX_RESPONSE_SIZE,
) -> dict:
    """Fetch parallelo di più URL con un singolo client httpx.

    Args:
        urls: Lista di URL da scaricare.
        timeout: Timeout per singola richiesta.
        max_size: Dimensione massima per risposta.

    Returns:
        Dict {url: (response, error_msg)} per ogni URL.
    """
    import httpx

    results = {}

    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=httpx.Timeout(timeout),
    ) as client:
        tasks = {url: fetch_url_async(url, client=client, timeout=timeout, max_size=max_size) for url in urls}

        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for url, result in zip(tasks.keys(), gathered):
            if isinstance(result, Exception):
                results[url] = (None, str(result))
            else:
                results[url] = result

    return results
