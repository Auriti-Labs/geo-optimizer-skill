# Security Reviewer — GEO Optimizer

## Scopo

Revisione sicurezza del codice GEO Optimizer. Il progetto processa URL arbitrari da input utente e genera output HTML — le superfici d'attacco principali sono SSRF, XSS e DoS.

## Aree di rischio

### 1. SSRF (Server-Side Request Forgery) — CRITICO
- **Dove**: `utils/http.py:fetch_url()`, qualsiasi funzione che accetta URL utente
- **Controllo**: ogni URL DEVE passare per `validators.resolve_and_validate_url()` PRIMA del fetch
- **Verificare**:
  - DNS pinning attivo (`_PinnedIPAdapter`) — no DNS rebinding
  - Redirect manuali con rivalidazione (`_fetch_with_manual_redirects`)
  - Blocklist reti: `_BLOCKED_NETWORKS` in `validators.py` copre RFC 1918, loopback, link-local, CGNAT, IPv4-mapped IPv6
  - Hostname bloccati: `_BLOCKED_HOSTNAMES` (localhost, metadata, 169.254.169.254)
  - Schema solo http/https (`_ALLOWED_SCHEMES`)
  - Credenziali embedded (`@` in netloc) bloccate
  - Nessun nuovo endpoint che fa fetch senza validazione

### 2. XSS (Cross-Site Scripting) — ALTO
- **Dove**: `cli/html_formatter.py`, `web/app.py` (report HTML), `web/badge.py` (SVG)
- **Verificare**:
  - Output HTML escaped correttamente (URL utente, titoli pagina, testi)
  - Nessun `f"<tag>{user_input}</tag>"` senza escape
  - Template HTML usano escape per default
  - Badge SVG non inietta input utente non sanitizzato

### 3. DoS (Denial of Service) — ALTO
- **Dove**: `utils/http.py`, `web/app.py`
- **Verificare**:
  - `MAX_RESPONSE_SIZE` (10 MB) rispettato in `_stream_response()`
  - `Content-Length` verificato prima del download
  - `_MAX_BODY_BYTES` (4 KB) nel middleware `BodySizeLimitMiddleware`
  - `MAX_SUB_SITEMAPS` (10) in `config.py` per sitemap index
  - `MAX_TOTAL_URLS` (10.000) per sitemap bomb
  - Timeout HTTP configurato (default 10s)
  - Rate limiting sulla web app

### 4. Path Traversal — MEDIO
- **Dove**: `cli/schema_cmd.py` (--file), qualsiasi file path da utente
- **Verificare**:
  - `validators.validate_safe_path()` usato prima di leggere/scrivere file
  - Whitelist estensioni (`allowed_extensions`)
  - `Path.resolve()` per risolvere symlink e `..`

### 5. Injection — BASSO (no database)
- **Dove**: N/A (toolkit stateless, no DB)
- **Verificare**: nessun `eval()`, `exec()`, `subprocess` con input utente

## Checklist per componente

### Nuovo endpoint web (`web/app.py`)
- [ ] Input validato con Pydantic model
- [ ] URL validato con `validate_public_url()`
- [ ] Output HTML escaped
- [ ] Rate limiting attivo
- [ ] CORS configurato correttamente
- [ ] Security headers presenti (CSP, X-Frame-Options, ecc.)

### Nuova funzione core (`core/*.py`)
- [ ] URL da `fetch_url()`, non `requests.get()`
- [ ] File da `validate_safe_path()`, non `open()` diretto
- [ ] Nessun print/logging di dati sensibili
- [ ] Dimensioni risposta verificate

### Nuovo formatter (`cli/*_formatter.py`)
- [ ] HTML output escaped (specialmente URL, titoli, testo utente)
- [ ] Nessun template string con input non sanitizzato
- [ ] File output usa `validate_safe_path()` per il percorso

## Classificazione severita

| Severita | Descrizione | Esempio |
|----------|-------------|---------|
| CRITICO | Accesso rete interna, esecuzione codice | SSRF bypass, eval() su input |
| ALTO | Data leak, DoS, XSS | HTML injection, response unbounded |
| MEDIO | Comportamento imprevisto | Path traversal, redirect loop |
| BASSO | Best practice mancante | Missing timeout, logging verboso |
