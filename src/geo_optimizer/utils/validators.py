"""
Validatori di input per GEO Optimizer.

Controlla URL (anti-SSRF) e percorsi file (anti-path-traversal)
prima di effettuare operazioni di rete o filesystem.
"""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

# Reti private/riservate da bloccare (RFC 1918, loopback, link-local, metadata cloud)
# Fix #80: range IPv6 espliciti per prevenire bypass SSRF tramite indirizzi IPv6.
# Nota: ::ffff:0:0/96 copre tutti i sotto-range ::ffff:* (IPv4-mapped),
# ma i range vengono elencati esplicitamente per chiarezza e audit sicurezza.
_BLOCKED_NETWORKS = [
    # ── IPv4 ──────────────────────────────────────────────────────────────────
    ipaddress.ip_network("0.0.0.0/8"),        # "this network" RFC 1122
    ipaddress.ip_network("127.0.0.0/8"),      # loopback IPv4
    ipaddress.ip_network("10.0.0.0/8"),       # privato RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),    # privato RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),   # privato RFC 1918
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT RFC 6598
    ipaddress.ip_network("192.0.0.0/24"),     # IETF Protocol Assignments
    ipaddress.ip_network("198.18.0.0/15"),    # benchmark testing RFC 2544
    ipaddress.ip_network("169.254.0.0/16"),   # link-local (AWS/GCP/Azure metadata)
    # ── IPv6 ──────────────────────────────────────────────────────────────────
    ipaddress.ip_network("::1/128"),          # loopback IPv6
    ipaddress.ip_network("fc00::/7"),         # unique local (ULA) RFC 4193: fc00:: - fdff::
    ipaddress.ip_network("fe80::/10"),        # link-local IPv6 RFC 4291
    # IPv4-mapped IPv6 (::ffff:0:0/96 copre tutti i sotto-range, elencati per chiarezza)
    ipaddress.ip_network("::ffff:0:0/96"),    # intero spazio IPv4-mapped (bypass comune)
    ipaddress.ip_network("::ffff:127.0.0.0/104"),  # loopback IPv4-mapped
    ipaddress.ip_network("::ffff:10.0.0.0/104"),   # RFC 1918 privato IPv4-mapped
    ipaddress.ip_network("::ffff:172.16.0.0/108"), # RFC 1918 privato IPv4-mapped
    ipaddress.ip_network("::ffff:192.168.0.0/112"), # RFC 1918 privato IPv4-mapped
]

_ALLOWED_SCHEMES = {"https", "http"}

# Nomi host interni noti
_BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata",
    "metadata.google.internal",
    "169.254.169.254",
}


def _is_ip_blocked(ip_obj) -> bool:
    """Verifica se un IP è privato/riservato usando le API standard di Python.

    Fallback per catturare reti non nella blocklist esplicita.
    """
    return (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_reserved
        or ip_obj.is_multicast
    )


def _validate_url_structure(url: str) -> tuple[bool, str | None, str | None]:
    """Valida la struttura dell'URL (schema, hostname, credenziali).

    Returns:
        (valido, errore, hostname) — hostname è None se non valido.
    """
    parsed = urlparse(url)

    # 1. Verifica schema
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False, f"Schema non consentito: '{parsed.scheme}'. Solo http/https.", None

    # 2. Estrai hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "Hostname mancante o non valido.", None

    # 3. Blocca nomi host interni noti
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return False, f"Host non consentito: '{hostname}'.", None

    # 4. Blocca URL con credenziali embedded (user:pass@host)
    if "@" in (parsed.netloc or ""):
        return False, "URL con credenziali embedded non consentiti.", None

    return True, None, hostname


def _check_ip_blocked(ip_str: str) -> tuple[bool, str | None]:
    """Verifica se un singolo indirizzo IP è in una rete bloccata.

    Returns:
        (bloccato, messaggio_errore) — bloccato=True se l'IP è da bloccare.
    """
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        # IP non parsabile: salta silenziosamente
        return False, None

    # Controlla blocklist esplicita
    for network in _BLOCKED_NETWORKS:
        if ip_obj in network:
            return True, (
                f"L'indirizzo '{ip_str}' risolto per l'host "
                f"è in una rete privata/riservata."
            )

    # Fallback: cattura reti private non nella blocklist esplicita
    if _is_ip_blocked(ip_obj):
        return True, (
            f"L'indirizzo '{ip_str}' risolto per l'host "
            f"è in una rete privata/riservata."
        )

    return False, None


def resolve_and_validate_url(url: str) -> tuple[bool, str | None, list[str]]:
    """Valida l'URL anti-SSRF e restituisce la lista di IP risolti.

    Risolve il DNS UNA SOLA VOLTA e restituisce gli IP validati.
    Questo previene attacchi DNS rebinding TOCTOU: il chiamante deve
    usare questi IP per la connessione effettiva, senza fare una seconda
    risoluzione DNS.

    Returns:
        (valido, errore, lista_ip_risolti)
        - lista_ip_risolti è vuota se DNS non risolvibile o URL non valido.
    """
    # Valida struttura URL
    ok, err, hostname = _validate_url_structure(url)
    if not ok:
        return False, err, []

    # Risolvi DNS e verifica che ogni IP risolto sia pubblico
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # DNS non risolvibile — non è un errore di sicurezza,
        # lascio che il fetch fallisca normalmente
        return True, None, []

    ip_validi = []
    for _, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        bloccato, msg = _check_ip_blocked(ip_str)
        if bloccato:
            hostname_display = hostname or "sconosciuto"
            # Riformula il messaggio con il nome host originale
            return False, (
                f"L'indirizzo '{ip_str}' risolto per '{hostname_display}' "
                f"è in una rete privata/riservata."
            ), []
        ip_validi.append(ip_str)

    return True, None, ip_validi


def validate_public_url(url: str) -> tuple[bool, str | None]:
    """
    Verifica che l'URL punti a un host pubblico, non a reti interne.

    Previene attacchi SSRF bloccando:
    - IP privati (RFC 1918), loopback, link-local
    - Cloud metadata endpoints (169.254.169.254)
    - Schema non consentiti (file://, ftp://, ecc.)
    - Nomi host interni (localhost, metadata)

    Returns:
        (True, None) se sicuro, (False, messaggio_errore) altrimenti.
    """
    ok, err, _ips = resolve_and_validate_url(url)
    return ok, err


def validate_safe_path(
    file_path: str,
    allowed_extensions: set[str] | None = None,
    must_exist: bool = False,
) -> tuple[bool, str | None]:
    """
    Verifica che un percorso file sia sicuro.

    Risolve symlink e path traversal, controlla l'estensione.

    Args:
        file_path: Percorso da validare.
        allowed_extensions: Set di estensioni consentite (es. {".html", ".htm"}).
        must_exist: Se True, verifica che il file esista.

    Returns:
        (True, None) se sicuro, (False, messaggio_errore) altrimenti.
    """
    try:
        resolved = Path(file_path).resolve()
    except (OSError, ValueError) as e:
        return False, f"Percorso non valido: {e}"

    if must_exist and not resolved.exists():
        return False, f"File non trovato: {resolved}"

    if must_exist and not resolved.is_file():
        return False, f"Non è un file: {resolved}"

    if allowed_extensions and resolved.suffix.lower() not in allowed_extensions:
        return False, (
            f"Estensione non consentita: '{resolved.suffix}'. Consentite: {', '.join(sorted(allowed_extensions))}"
        )

    return True, None


def url_belongs_to_domain(url: str, domain: str) -> bool:
    """
    Verifica l'appartenenza esatta al dominio, senza substring match.

    Gestisce subdomain legittimi (es. blog.example.com per example.com).
    Blocca URL con credenziali embedded (@).

    Args:
        url: URL completo da verificare.
        domain: Dominio di riferimento (es. "example.com").

    Returns:
        True se l'URL appartiene al dominio.
    """
    parsed = urlparse(url)
    netloc = parsed.netloc

    # Blocca URL con credenziali embedded
    if "@" in netloc:
        return False

    # Rimuove porta se presente
    hostname = netloc.split(":")[0].lower()
    domain_lower = domain.lower()

    # Corrispondenza esatta o subdomain legittimo
    return hostname == domain_lower or hostname.endswith("." + domain_lower)
