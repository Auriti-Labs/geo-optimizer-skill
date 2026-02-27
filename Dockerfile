# ─── GEO Optimizer — Docker image ────────────────────────────────────────────
# Multi-stage build per immagine leggera (~120MB)
#
# Uso:
#   docker build -t geo-optimizer .
#   docker run geo-optimizer audit --url https://example.com
#   docker run geo-optimizer audit --url https://example.com --format json
#
# Con output su file:
#   docker run -v $(pwd):/output geo-optimizer audit --url https://example.com --format html --output /output/report.html

# ─── Stage 1: build ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Copia solo i file necessari per l'installazione
COPY pyproject.toml README.md ./
COPY src/ src/

# Installa il pacchetto in una directory isolata
RUN pip install --no-cache-dir --prefix=/install .

# ─── Stage 2: runtime ───────────────────────────────────────────────────────
FROM python:3.12-slim

# Metadati immagine
LABEL org.opencontainers.image.title="GEO Optimizer" \
      org.opencontainers.image.description="Audit your website's visibility to AI search engines" \
      org.opencontainers.image.url="https://github.com/auriti-labs/geo-optimizer-skill" \
      org.opencontainers.image.source="https://github.com/auriti-labs/geo-optimizer-skill" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Auriti Labs"

# Copia pacchetto installato dal builder
COPY --from=builder /install /usr/local

# Utente non-root per sicurezza
RUN useradd --create-home --shell /bin/bash geo
USER geo
WORKDIR /home/geo

# Variabili d'ambiente per produzione
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Health check per orchestratori (Docker Compose, K8s)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["geo", "--help"]

# Punto di ingresso: CLI geo
ENTRYPOINT ["geo"]

# Default: mostra help
CMD ["--help"]
