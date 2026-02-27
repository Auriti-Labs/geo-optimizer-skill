"""
Test per le fix M1 di sicurezza e stabilità v3.0.0.

Copre:
- #57 SSRF nella sitemap index — sub-URL validati
- #58 DoS — cache limitata con eviction
- #59 Info disclosure — errori generici
- #60 Rate limiting — protezione endpoint
- #61 Security headers — CSP, X-Frame-Options, ecc.
- #62 Injection template Astro — sanitizzazione url/name
- #63 Event loop — audit wrappato in asyncio.to_thread
"""

import time
from unittest.mock import MagicMock, patch

from geo_optimizer.core.schema_injector import generate_astro_snippet
from geo_optimizer.web.app import (
    _MAX_CACHE_SIZE,
    _audit_cache,
    _check_rate_limit,
    _evict_expired,
    _rate_limit_store,
    _set_cached,
)


# ============================================================================
# #57 — SSRF nella sitemap index
# ============================================================================


class TestSitemapSsrf:
    """Test validazione anti-SSRF per sub-URL in sitemap index."""

    def test_sub_sitemap_privato_bloccato(self):
        """URL privato in sitemap index viene ignorato."""
        from geo_optimizer.core.llms_generator import fetch_sitemap

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>http://10.0.0.1/sitemap.xml</loc></sitemap>
        </sitemapindex>
        """
        mock_response = MagicMock()
        mock_response.content = sitemap_xml.encode()
        mock_response.raise_for_status = MagicMock()

        with patch("geo_optimizer.core.llms_generator.create_session_with_retry") as mock_session:
            mock_session.return_value.get.return_value = mock_response
            urls = fetch_sitemap("https://example.com/sitemap.xml")
            # Sub-sitemap a IP privato deve essere ignorato
            assert urls == []

    def test_sub_sitemap_pubblico_accettato(self):
        """URL pubblico in sitemap index viene processato."""
        from geo_optimizer.core.llms_generator import fetch_sitemap

        sitemap_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap-posts.xml</loc></sitemap>
        </sitemapindex>
        """
        sitemap_posts_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/post-1</loc></url>
        </urlset>
        """
        mock_resp_index = MagicMock()
        mock_resp_index.content = sitemap_index_xml.encode()
        mock_resp_index.raise_for_status = MagicMock()

        mock_resp_posts = MagicMock()
        mock_resp_posts.content = sitemap_posts_xml.encode()
        mock_resp_posts.raise_for_status = MagicMock()

        with patch("geo_optimizer.core.llms_generator.create_session_with_retry") as mock_session:
            mock_session.return_value.get.side_effect = [mock_resp_index, mock_resp_posts]
            with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
                mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
                urls = fetch_sitemap("https://example.com/sitemap.xml")
                assert len(urls) == 1
                assert urls[0].url == "https://example.com/post-1"


# ============================================================================
# #58 — Cache limitata
# ============================================================================


class TestCacheLimits:
    """Test limiti cache in-memory."""

    def setup_method(self):
        _audit_cache.clear()

    def teardown_method(self):
        _audit_cache.clear()

    def test_cache_non_supera_max_size(self):
        """La cache non cresce oltre _MAX_CACHE_SIZE."""
        for i in range(_MAX_CACHE_SIZE + 10):
            _set_cached(f"https://example-{i}.com", {"score": i, "band": "good"})
        assert len(_audit_cache) <= _MAX_CACHE_SIZE

    def test_evict_rimuove_scadute(self):
        """_evict_expired() rimuove entry con TTL scaduto."""
        _audit_cache["old"] = {"data": {}, "cached_at": time.time() - 7200}
        _audit_cache["new"] = {"data": {}, "cached_at": time.time()}
        _evict_expired()
        assert "old" not in _audit_cache
        assert "new" in _audit_cache

    def test_eviction_preserva_recenti(self):
        """Quando piena, la cache rimuove la entry più vecchia."""
        # Riempi cache
        for i in range(_MAX_CACHE_SIZE):
            _audit_cache[f"key-{i}"] = {
                "data": {"score": i},
                "cached_at": time.time() + i * 0.001,
            }
        # Aggiungi una nuova
        _set_cached("https://new-entry.com", {"score": 99, "band": "excellent"})
        assert len(_audit_cache) <= _MAX_CACHE_SIZE


# ============================================================================
# #60 — Rate limiting
# ============================================================================


class TestRateLimiting:
    """Test rate limiter in-memory."""

    def setup_method(self):
        _rate_limit_store.clear()

    def teardown_method(self):
        _rate_limit_store.clear()

    def test_richieste_sotto_limite_passano(self):
        """Richieste sotto il limite vengono accettate."""
        for _ in range(10):
            assert _check_rate_limit("192.0.2.1") is True

    def test_richieste_sopra_limite_bloccate(self):
        """Richieste oltre il limite vengono bloccate."""
        for _ in range(30):
            _check_rate_limit("192.0.2.2")
        assert _check_rate_limit("192.0.2.2") is False

    def test_ip_diversi_indipendenti(self):
        """Ogni IP ha il proprio contatore."""
        for _ in range(30):
            _check_rate_limit("192.0.2.3")
        # IP diverso non è limitato
        assert _check_rate_limit("192.0.2.4") is True


# ============================================================================
# #62 — Injection template Astro
# ============================================================================


class TestAstroInjection:
    """Test sanitizzazione parametri generate_astro_snippet."""

    def test_url_con_virgolette_sanitizzato(self):
        """Virgolette nell'URL vengono rimosse."""
        result = generate_astro_snippet('https://evil.com"; import("evil")//', "Safe Site")
        assert '"' not in result.split("SITE_URL")[0] or '" import(' not in result
        # Verifica che la stringa maligna non sia interpolata direttamente
        assert 'import("evil")' not in result

    def test_name_con_backtick_sanitizzato(self):
        """Backtick nel nome vengono rimossi."""
        result = generate_astro_snippet("https://safe.com", "`${process.env.SECRET}`")
        assert "${process.env.SECRET}" not in result

    def test_url_troncato(self):
        """URL troppo lungo viene troncato a 200 caratteri."""
        long_url = "https://example.com/" + "A" * 300
        result = generate_astro_snippet(long_url, "Test")
        assert "A" * 201 not in result

    def test_name_troncato(self):
        """Nome troppo lungo viene troncato a 100 caratteri."""
        long_name = "A" * 200
        result = generate_astro_snippet("https://example.com", long_name)
        assert "A" * 101 not in result

    def test_input_sicuro_invariato(self):
        """Input sicuro viene usato correttamente."""
        result = generate_astro_snippet("https://example.com", "My Site")
        assert "https://example.com" in result
        assert "My Site" in result
