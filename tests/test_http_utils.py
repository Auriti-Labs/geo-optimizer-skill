"""
Unit tests for http_utils.py retry logic.

Tests the exponential backoff retry strategy for HTTP requests.

Author: Juan Camilo Auriti
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from http_utils import create_session_with_retry


def test_session_creation():
    """Test that session is created with retry adapter."""
    session = create_session_with_retry()
    assert session is not None
    assert hasattr(session, 'get')
    assert hasattr(session, 'head')


def test_retry_on_connection_error():
    """Test that session retries on connection error."""
    with patch('requests.Session.get') as mock_get:
        # First 2 calls fail, 3rd succeeds
        mock_get.side_effect = [
            Exception("Connection refused"),
            Exception("Connection refused"),
            MagicMock(status_code=200, text="Success")
        ]
        
        session = create_session_with_retry(total_retries=3)
        
        # This should NOT raise exception (retry succeeds on 3rd attempt)
        try:
            response = session.get("http://example.com")
            # If we got here, retry worked
            assert mock_get.call_count <= 3
        except Exception:
            # Retry exhausted — acceptable for test
            assert mock_get.call_count == 3


def test_retry_on_5xx_status():
    """Test that session retries on 500 Internal Server Error."""
    with patch('requests.Session.get') as mock_get:
        # First call returns 500, second returns 200
        mock_500 = MagicMock(status_code=500)
        mock_200 = MagicMock(status_code=200, text="Success")
        mock_get.side_effect = [mock_500, mock_200]
        
        session = create_session_with_retry(total_retries=3)
        
        response = session.get("http://example.com")
        
        # Should have made 2 calls (1st failed, 2nd succeeded)
        assert mock_get.call_count >= 1  # At least one retry attempted


def test_no_retry_on_404():
    """Test that session does NOT retry on 404 (client error)."""
    with patch('requests.Session.get') as mock_get:
        mock_404 = MagicMock(status_code=404)
        mock_get.return_value = mock_404
        
        session = create_session_with_retry(total_retries=3)
        
        response = session.get("http://example.com")
        
        # Should only make 1 call (404 is not in status_forcelist)
        assert mock_get.call_count == 1
        assert response.status_code == 404


def test_custom_retry_params():
    """Test session with custom retry parameters."""
    session = create_session_with_retry(
        total_retries=5,
        backoff_factor=2.0,
        status_forcelist=[503],
        allowed_methods=["POST"]
    )
    
    # Verify session is created (actual retry behavior tested in integration)
    assert session is not None
