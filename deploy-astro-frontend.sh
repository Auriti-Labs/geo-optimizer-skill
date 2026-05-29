#!/bin/bash
#
# Deploy veloce — GEO Optimizer Frontend Astro
# Uso: ssh geoapp@51.68.234.198 "bash -s" < deploy-astro-frontend.sh
# Oppure: copia sul server ed esegui come geoapp
#
set -e

echo "=== GEO Optimizer — Deploy Astro Frontend ==="
echo "Data: $(date)"
echo ""

APP_DIR="/home/geoapp/geo-optimizer-skill"
IMAGE_NAME="geo-optimizer-web"
CONTAINER_NAME="geo-web"
PORT=8000

cd "${APP_DIR}"

echo "[1/5] Git pull..."
git fetch origin
git reset --hard origin/main
git pull origin main

echo "[2/5] Build Docker image (Python + Node + Astro)..."
docker build -t "${IMAGE_NAME}" -f Dockerfile.web .

echo "[3/5] Stop container esistente..."
docker stop "${CONTAINER_NAME}" 2>/dev/null || true
docker rm "${CONTAINER_NAME}" 2>/dev/null || true

echo "[4/5] Avvio nuovo container..."
# Use host networking so Uvicorn sees Nginx as a trusted local proxy.
# This keeps ProxyHeadersMiddleware effective and prevents Starlette
# directory redirects from generating http:// Location headers.
#
# Optional: source ENV_FILE to inject secrets (GEO_STATS_API_KEY, etc.)
# Default location: /home/debian/.geo-web.env (mode 600)
ENV_FILE="${GEO_WEB_ENV_FILE:-/home/debian/.geo-web.env}"
ENV_ARG=""
if [ -f "${ENV_FILE}" ]; then
    echo "  Loading env from ${ENV_FILE}"
    ENV_ARG="--env-file ${ENV_FILE}"
fi

docker run -d \
    --name "${CONTAINER_NAME}" \
    --network host \
    -e ALLOWED_ORIGINS=https://geoready.dev \
    -e GEO_LANG=it \
    -e PORT=${PORT} \
    -e GEO_STATS_API_URL=https://agencypilot.it/api/geo-stats \
    ${ENV_ARG} \
    --restart unless-stopped \
    "${IMAGE_NAME}"

echo "[5/5] Health check..."
sleep 5
if curl -sf http://localhost:${PORT}/health > /dev/null; then
    echo ""
    echo "[SUCCESS] Deploy completato!"
    echo "  - Homepage:    https://geoready.dev/"
    echo "  - Health:      http://localhost:${PORT}/health"
    echo "  - API:         https://geoready.dev/api/audit"
    echo ""
    echo "Log: journalctl -u geo-web -f"
else
    echo "[ERROR] Health check fallito"
    docker logs "${CONTAINER_NAME}" --tail 30
    exit 1
fi
