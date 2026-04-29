"""
Test per le fix critiche di sicurezza v3.0.0.

Copre:
- #55 XSS nel badge SVG — parametro label sanitizzato
- #56 SSRF bypass — reti IP aggiuntive bloccate
"""

from unittest.mock import patch

from geo_optimizer.utils.validators import validate_public_url
from geo_optimizer.web.badge import (
    BAND_COLORS,
    _MAX_LABEL_LENGTH,
    _svg_escape,
    generate_badge_svg,
)


# ============================================================================
# #55 — XSS nel badge SVG
# ============================================================================


class TestSvgEscape:
    """Test escape XML/SVG per prevenire XSS."""

    def test_escape_angolari(self):
        assert _svg_escape("<script>") == "&lt;script&gt;"

    def test_escape_ampersand(self):
        assert _svg_escape("A & B") == "A &amp; B"

    def test_escape_virgolette(self):
        assert _svg_escape('test "quoted"') == "test &quot;quoted&quot;"

    def test_escape_apice(self):
        assert _svg_escape("it's") == "it&#x27;s"

    def test_stringa_sicura_invariata(self):
        assert _svg_escape("GEO Score") == "GEO Score"

    def test_stringa_vuota(self):
        assert _svg_escape("") == ""


class TestBadgeSvgXss:
    """Test prevenzione XSS nel generatore badge SVG."""

    def test_label_con_script_injection(self):
        """Payload XSS nel label viene neutralizzato."""
        svg = generate_badge_svg(85, "good", label='"></text><script>alert("xss")</script><text>')
        assert "<script>" not in svg
        assert "&lt;script&gt;" in svg

    def test_label_con_svg_event_handler(self):
        """Event handler SVG nel label viene neutralizzato."""
        svg = generate_badge_svg(90, "excellent", label='" onload="alert(1)')
        assert "onload" not in svg or "&quot;" in svg
        # Il " viene escapato a &quot;, rompendo l'injection
        assert "&quot;" in svg

    def test_label_troncata_a_max_length(self):
        """Label troppo lunga viene troncata."""
        long_label = "A" * 100
        svg = generate_badge_svg(50, "foundation", label=long_label)
        # Verifica che la label nel SVG non contenga 100 "A"
        assert "A" * (_MAX_LABEL_LENGTH + 1) not in svg

    def test_band_non_valida_diventa_critical(self):
        """Band non nella whitelist usa 'critical'."""
        svg = generate_badge_svg(50, "nonexistent")
        assert BAND_COLORS["critical"] in svg

    def test_score_clampato_min(self):
        """Score negativo viene portato a 0."""
        svg = generate_badge_svg(-10, "critical")
        assert "0/100" in svg

    def test_score_clampato_max(self):
        """Score > 100 viene portato a 100."""
        svg = generate_badge_svg(999, "excellent")
        assert "100/100" in svg

    def test_svg_valido_con_input_normale(self):
        """Badge con input normali genera SVG valido."""
        svg = generate_badge_svg(85, "good", label="GEO Score")
        assert svg.startswith("<svg")
        assert "GEO Score" in svg
        assert "85/100" in svg
        assert BAND_COLORS["good"] in svg
        assert 'role="img"' in svg

    def test_aria_label_escapata(self):
        """aria-label contiene la label escapata."""
        svg = generate_badge_svg(75, "good", label="Test <Label>")
        assert 'aria-label="Test &lt;Label&gt;: 75/100"' in svg

    def test_title_escapata(self):
        """Tag title contiene la label escapata."""
        svg = generate_badge_svg(75, "good", label="Test <Label>")
        assert "<title>Test &lt;Label&gt;: 75/100</title>" in svg

    def test_tutte_le_band_valide(self):
        """Tutte le band nella whitelist producono il colore corretto."""
        for band, color in BAND_COLORS.items():
            svg = generate_badge_svg(50, band)
            assert color in svg


# ============================================================================
# #56 — SSRF bypass con reti IP aggiuntive
# ============================================================================


class TestSsrfBypassNetworks:
    """Test blocco reti IP usate per bypass SSRF."""

    def test_blocca_zero_network(self):
        """0.0.0.0/8 — 'this network' RFC 1122."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("0.0.0.1", 0))]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False
            assert "non-public" in err.lower()

    def test_blocca_cgnat_rfc6598(self):
        """100.64.0.0/10 — CGNAT RFC 6598."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("100.64.0.1", 0))]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False

    def test_blocca_ietf_protocol_assignments(self):
        """192.0.0.0/24 — IETF Protocol Assignments."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("192.0.0.1", 0))]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False

    def test_blocca_benchmark_rfc2544(self):
        """198.18.0.0/15 — Benchmark testing RFC 2544."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("198.18.0.1", 0))]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False

    def test_blocca_ipv4_mapped_ipv6(self):
        """::ffff:127.0.0.1 — IPv4-mapped IPv6 bypass."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(10, 1, 6, "", ("::ffff:127.0.0.1", 0, 0, 0))]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False

    def test_blocca_ipv4_mapped_ipv6_privato(self):
        """::ffff:10.0.0.1 — IPv4-mapped IPv6 con IP privato."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(10, 1, 6, "", ("::ffff:10.0.0.1", 0, 0, 0))]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False

    def test_ip_pubblico_passa(self):
        """IP pubblico legittimo non viene bloccato."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("8.8.8.8", 0))]
            ok, err = validate_public_url("https://example.com")
            assert ok is True
            assert err is None

    def test_blocca_multicast(self):
        """Indirizzi multicast bloccati dal fallback is_multicast."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("224.0.0.1", 0))]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False

    def test_reti_rfc1918_ancora_bloccate(self):
        """Reti RFC 1918 originali continuano a essere bloccate."""
        test_ips = ["10.0.0.1", "172.16.0.1", "192.168.1.1"]
        for ip in test_ips:
            with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
                mock_dns.return_value = [(2, 1, 6, "", (ip, 0))]
                ok, err = validate_public_url("https://evil.example.com")
                assert ok is False, f"{ip} dovrebbe essere bloccato"

    def test_loopback_ipv6(self):
        """::1 — loopback IPv6 bloccato."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(10, 1, 6, "", ("::1", 0, 0, 0))]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False
