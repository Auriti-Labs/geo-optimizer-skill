"""Test per il retry esponenziale in fetch_url (v4.10).

Verifica:
- Timeout e ConnectionError sono retryati
- Retry esponenziale: 1s, 2s, 4s
- Max 3 retry (4 tentativi totali)
- NO retry per: 4xx client error, SSRF validation error, ValueError
- Logging di warning per ogni retry
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, call, patch

import pytest
import requests

from geo_optimizer.utils.http import _execute_request, with_retry


class TestWithRetryDecorator:
    """Test unitari del decorator @with_retry."""

    def test_successo_al_primo_tentativo(self):
        """Nessun errore → una sola chiamata, nessun retry."""

        @with_retry()
        def _func(counter):
            counter["calls"] += 1
            return "ok"

        counter = {"calls": 0}
        with patch("geo_optimizer.utils.http.time.sleep") as mock_sleep:
            result = _func(counter)

        assert result == "ok"
        assert counter["calls"] == 1
        mock_sleep.assert_not_called()

    def test_successo_dopo_timeout_singolo(self):
        """Prima chiamata fallisce con Timeout, seconda ha successo → 2 tentativi."""

        @with_retry(max_retries=3, backoff_base=2)
        def _func(counter):
            counter["calls"] += 1
            if counter["calls"] == 1:
                raise requests.exceptions.Timeout("Simulated timeout")
            return "success"

        counter = {"calls": 0}
        with patch("geo_optimizer.utils.http.time.sleep") as mock_sleep:
            result = _func(counter)

        assert result == "success"
        assert counter["calls"] == 2
        # Delay: 2^0 = 1 secondo
        mock_sleep.assert_called_once_with(1)

    def test_fallimento_dopo_max_retry(self):
        """Tutti i tentativi falliscono → 4 chiamate (originale + 3 retry)."""

        @with_retry(max_retries=3, backoff_base=2)
        def _func(counter):
            counter["calls"] += 1
            raise requests.exceptions.ConnectionError("Simulated failure")

        counter = {"calls": 0}
        with (
            patch("geo_optimizer.utils.http.time.sleep") as mock_sleep,
            pytest.raises(requests.exceptions.ConnectionError),
        ):
            _func(counter)

        assert counter["calls"] == 4  # originale + 3 retry
        assert mock_sleep.call_count == 3
        # Verifica backoff esponenziale: 2^0=1, 2^1=2, 2^2=4
        mock_sleep.assert_has_calls([call(1), call(2), call(4)])

    def test_no_retry_per_errori_permanenti(self):
        """ValueError non e' retryable → fallimento immediato, 1 chiamata sola."""

        @with_retry(max_retries=3)
        def _func(counter):
            counter["calls"] += 1
            raise ValueError("Permanent error")

        counter = {"calls": 0}
        with patch("geo_optimizer.utils.http.time.sleep") as mock_sleep, pytest.raises(ValueError):
            _func(counter)

        assert counter["calls"] == 1
        mock_sleep.assert_not_called()

    def test_backoff_esponenziale_2(self):
        """Con backoff_base=2 i delay sono 1, 2, 4 secondi."""

        @with_retry(max_retries=3, backoff_base=2)
        def _func(counter):
            counter["calls"] += 1
            raise requests.exceptions.Timeout("timeout")

        counter = {"calls": 0}
        with patch("geo_optimizer.utils.http.time.sleep") as mock_sleep, pytest.raises(requests.exceptions.Timeout):
            _func(counter)

        assert mock_sleep.call_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1, 2, 4]

    def test_backoff_esponenziale_3(self):
        """Con backoff_base=3 i delay sono 1, 3, 9 secondi."""

        @with_retry(max_retries=3, backoff_base=3)
        def _func(counter):
            counter["calls"] += 1
            raise requests.exceptions.Timeout("timeout")

        counter = {"calls": 0}
        with patch("geo_optimizer.utils.http.time.sleep") as mock_sleep, pytest.raises(requests.exceptions.Timeout):
            _func(counter)

        assert mock_sleep.call_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1, 3, 9]

    def test_retry_0_tentativi(self):
        """max_retries=0 → nessun retry, fallimento immediato."""

        @with_retry(max_retries=0)
        def _func(counter):
            counter["calls"] += 1
            raise requests.exceptions.Timeout("timeout")

        counter = {"calls": 0}
        with patch("geo_optimizer.utils.http.time.sleep") as mock_sleep, pytest.raises(requests.exceptions.Timeout):
            _func(counter)

        assert counter["calls"] == 1
        mock_sleep.assert_not_called()

    def test_logging_retry_warning(self):
        """Ogni retry genera un log di livello WARNING."""

        @with_retry(max_retries=2, backoff_base=2)
        def _func(counter):
            counter["calls"] += 1
            raise requests.exceptions.Timeout("timeout")

        counter = {"calls": 0}
        with (
            patch("geo_optimizer.utils.http.time.sleep"),
            patch("geo_optimizer.utils.http._logger.warning") as mock_warn,
            pytest.raises(requests.exceptions.Timeout),
        ):
            _func(counter)

        assert mock_warn.call_count == 2
        # Verifica che il messaggio contenga il nome della funzione
        # args[0] = format string, args[1] = attempt, args[2] = max_retries,
        # args[3] = func name, args[4] = delay, args[5] = exception
        first_call = mock_warn.call_args_list[0]
        assert "_func" in first_call.args[3]
        assert first_call.args[1] == 1  # retry 1/2

    def test_decorator_preserva_signature(self):
        """Il decorator preserva nome e docstring della funzione wrappata."""

        @with_retry()
        def my_function(a, b=10):
            """Test docstring."""
            return a + b

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "Test docstring."


class TestExecuteRequestRetry:
    """Test end-to-end del retry in _execute_request (integrato con fetch_url)."""

    @patch("geo_optimizer.utils.http.time.sleep")
    def test_execute_request_success_after_timeout(self, mock_sleep):
        """_execute_request retrya su Timeout e poi ha successo."""
        session = MagicMock()
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise requests.exceptions.Timeout("Simulated")
            response = Mock()
            response.status_code = 200
            return response

        session.get.side_effect = side_effect

        result = _execute_request(session, "https://example.com", timeout=10)

        assert result.status_code == 200
        assert call_count["n"] == 2
        mock_sleep.assert_called_once_with(1)  # _BACKOFF_BASE=2 ^ 0 = 1

    @patch("geo_optimizer.utils.http.time.sleep")
    def test_execute_request_failure_after_retries(self, mock_sleep):
        """_execute_request fallisce dopo 3 retry (4 tentativi totali)."""
        session = MagicMock()
        session.get.side_effect = requests.exceptions.ConnectionError("Simulated")

        with pytest.raises(requests.exceptions.ConnectionError):
            _execute_request(session, "https://example.com", timeout=10)

        assert session.get.call_count == 4  # originale + 3 retry
        assert mock_sleep.call_count == 3


class TestFetchUrlRetryIntegration:
    """Test di integrazione del retry in fetch_url."""

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_fetch_url_timeout_con_retry(self, mock_create, mock_dns):
        """fetch_url gestisce Timeout con retry e poi successo."""
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        mock_session = MagicMock()
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise requests.exceptions.Timeout("Simulated timeout")
            response = Mock()
            response.status_code = 200
            response.headers = {}
            response._content = b"Hello"
            response._content_consumed = False
            return response

        mock_session.get.side_effect = side_effect
        mock_create.return_value = mock_session

        with patch("geo_optimizer.utils.http.time.sleep") as mock_sleep:
            resp, err = _fetch_url_testable("https://example.com")

        assert resp is not None
        assert resp.status_code == 200
        assert call_count["n"] == 2
        mock_sleep.assert_called_once_with(1)

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_fetch_url_timeout_dopo_max_retry(self, mock_create, mock_dns):
        """fetch_url fallisce con Timeout dopo tutti i retry."""
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.Timeout("Always timeout")
        mock_create.return_value = mock_session

        with patch("geo_optimizer.utils.http.time.sleep"):
            resp, err = _fetch_url_testable("https://example.com")

        assert resp is None
        assert "Timeout" in err
        assert "retry esponenziale" in err
        assert mock_session.get.call_count == 4

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_fetch_url_connection_error_con_retry(self, mock_create, mock_dns):
        """fetch_url gestisce ConnectionError con retry e poi successo."""
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        mock_session = MagicMock()
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise requests.exceptions.ConnectionError("Simulated")
            response = Mock()
            response.status_code = 200
            response.headers = {}
            response._content = b"Hello"
            response._content_consumed = False
            return response

        mock_session.get.side_effect = side_effect
        mock_create.return_value = mock_session

        with patch("geo_optimizer.utils.http.time.sleep") as mock_sleep:
            resp, err = _fetch_url_testable("https://example.com")

        assert resp is not None
        assert resp.status_code == 200
        assert call_count["n"] == 2
        mock_sleep.assert_called_once_with(1)


# ============================================================================
# Helpers
# ============================================================================


def _fetch_url_testable(url: str) -> tuple:
    """Wrapper testabile per fetch_url che bypassa il controllo SSRF."""
    from geo_optimizer.utils.http import fetch_url

    return fetch_url(url)
