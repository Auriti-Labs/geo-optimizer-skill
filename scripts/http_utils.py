"""
HTTP utilities with retry logic and exponential backoff.

Provides robust HTTP session with automatic retry for transient failures:
- Connection errors
- Timeouts
- Server errors (5xx)
- Rate limits (429)

Author: Juan Camilo Auriti
Created: 2026-02-21
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session_with_retry(
    total_retries=3,
    backoff_factor=1.0,
    status_forcelist=None,
    allowed_methods=None
):
    """
    Create requests session with exponential backoff retry strategy.
    
    Args:
        total_retries (int): Maximum number of retry attempts (default: 3)
        backoff_factor (float): Backoff multiplier (default: 1.0)
            - Retry 1: backoff_factor * 1 = 1s
            - Retry 2: backoff_factor * 2 = 2s
            - Retry 3: backoff_factor * 4 = 4s
        status_forcelist (list): HTTP status codes to retry (default: [408, 429, 500, 502, 503, 504])
        allowed_methods (list): HTTP methods to retry (default: ["GET", "HEAD"])
    
    Returns:
        requests.Session: Configured session with retry adapter
        
    Example:
        >>> session = create_session_with_retry()
        >>> response = session.get("https://example.com", timeout=10)
    """
    if status_forcelist is None:
        status_forcelist = [408, 429, 500, 502, 503, 504]
    
    if allowed_methods is None:
        allowed_methods = ["GET", "HEAD"]
    
    session = requests.Session()
    
    retry_strategy = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods,
        raise_on_status=False  # Don't raise exception on retry exhaustion
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


# Default session instance for import convenience
default_session = create_session_with_retry()
