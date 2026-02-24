"""
HTTP utilities with retry logic and exponential backoff.

Provides robust HTTP session with automatic retry for transient failures:
- Connection errors
- Timeouts
- Server errors (5xx)
- Rate limits (429)
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from geo_optimizer.models.config import HEADERS


def create_session_with_retry(
    total_retries=3,
    backoff_factor=1.0,
    status_forcelist=None,
    allowed_methods=None,
):
    """
    Create requests session with exponential backoff retry strategy.

    Args:
        total_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Backoff multiplier (default: 1.0)
        status_forcelist: HTTP status codes to retry
        allowed_methods: HTTP methods to retry (default: ["GET", "HEAD"])

    Returns:
        requests.Session: Configured session with retry adapter
    """
    if status_forcelist is None:
        status_forcelist = [408, 429, 500, 502, 503, 504]
    if allowed_methods is None:
        allowed_methods = ["GET", "HEAD"]

    session = requests.Session()
    session.headers.update(HEADERS)

    retry_strategy = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def fetch_url(url, timeout=10):
    """
    Fetch a URL with automatic retry on transient failures.

    Returns:
        tuple: (response, error_msg) where response is None on failure
    """
    try:
        session = create_session_with_retry(
            total_retries=3,
            backoff_factor=1.0,
            status_forcelist=[408, 429, 500, 502, 503, 504],
        )
        r = session.get(url, timeout=timeout, allow_redirects=True)
        return r, None
    except requests.exceptions.Timeout:
        return None, f"Timeout ({timeout}s) after 3 retries"
    except requests.exceptions.ConnectionError as e:
        return None, f"Connection failed after 3 retries: {e}"
    except Exception as e:
        return None, str(e)
