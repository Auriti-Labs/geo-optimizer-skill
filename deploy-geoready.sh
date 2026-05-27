#!/bin/bash
#
# Deploy script per GEO Optimizer Web su geoready.dev
# Server: Debian 12+ su 51.68.234.198
#
# Uso: ssh debian@51.68.234.198 "bash -s" < deploy-geoready.sh
#

set -e

echo "=== GEO Optimizer Web - Deploy Script ==="
echo "Data: $(date)"
echo "Host: $(hostname)"
echo ""

# ─── Configurazione ─────────────────────────────────────────────────────────────
APP_USER="geoapp"
APP_DIR="/home/${APP_USER}/geo-optimizer-skill"
DOMAIN="geoready.dev"
SERVER_IP="51.68.234.198"
APP_PORT=8000

# ─── Verifica privilegi root ────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo "Errore: Questo script deve essere eseguito come root"
    exit 1
fi

echo "✓ Eseguito come root"

# ─── Funzioni ausiliarie ────────────────────────────────────────────────────────
log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

log_success() {
    echo "[SUCCESS] $1"
}

# ─── Step 1: Update e dipendenze ────────────────────────────────────────────────
log_info "Step 1: Update sistema e installazione dipendenze..."

apt update -y
apt upgrade -y

# Dipendenze di sistema
apt install -y \
    curl \
    gnupg \
    lsb-release \
    ca-certificates \
    nginx \
    certbot \
    python3-certbot-nginx \
    python3-pip \
    git \
    ufw

log_success "Dipendenze installate"

# ─── Step 2: Installazione Docker ───────────────────────────────────────────────
log_info "Step 2: Installazione Docker..."

# Aggiungi repository Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt update -y
    apt install -y docker-ce docker-ce-cli containerd.io
fi

# Aggiungi utente geoapp a docker group
usermod -aG docker "${APP_USER}" 2>/dev/null || true

# Avvia e abilita Docker
systemctl enable docker
systemctl start docker

log_success "Docker installato e avviato"

# ─── Step 3: Installazione Docker Compose ───────────────────────────────────────
log_info "Step 3: Installazione Docker Compose..."

if ! command -v docker-compose &> /dev/null; then
    curl -SL "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

docker-compose --version
log_success "Docker Compose installato"

# ─── Step 4: Creazione utente e directory ────────────────────────────────────────
log_info "Step 4: Configurazione utente e directory..."

if ! id "${APP_USER}" &> /dev/null; then
    useradd -m -s /bin/bash "${APP_USER}"
    log_info "Utente ${APP_USER} creato"
else
    log_info "Utente ${APP_USER} esiste già"
fi

# Crea directory
mkdir -p "${APP_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
chmod 755 "${APP_DIR}"

log_success "Directory configurata: ${APP_DIR}"

# ─── Step 5: Clone del repository ────────────────────────────────────────────────
log_info "Step 5: Clone del repository geo-optimizer-skill..."

if [ ! -d "${APP_DIR}/.git" ]; then
    su - "${APP_USER}" -c "cd ${APP_DIR} && git clone https://github.com/Auriti-Labs/geo-optimizer-skill.git ."
else
    su - "${APP_USER}" -c "cd ${APP_DIR} && git fetch --all && git checkout main && git pull origin main"
fi

log_success "Repository clonato/aggiornato"

# ─── Step 6: Build immagine Docker ───────────────────────────────────────────────
log_info "Step 6: Build immagine Docker..."

su - "${APP_USER}" -c "cd ${APP_DIR} && docker build -t geo-optimizer-web -f Dockerfile.web ."

log_success "Immagine geo-optimizer-web buildata"

# ─── Step 7: Configurazione Nginx ────────────────────────────────────────────────
log_info "Step 7: Configurazione Nginx..."

# Crea configurazione Nginx
cat > /etc/nginx/sites-available/${DOMAIN} << 'NGINX_EOF'
# GEO Optimizer Web - Nginx configuration

upstream geo_app {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP → HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};

    # ACME challenge per Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN} www.${DOMAIN};

    # SSL Certificate
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/${DOMAIN}/chain.pem;

    # SSL settings
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    ssl_protocols TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/${DOMAIN}.access.log;
    error_log /var/log/nginx/${DOMAIN}.error.log;

    # Proxy pass al FastAPI
    location / {
        proxy_pass http://geo_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;

        # Body size limit
        client_max_body_size 4k;
    }

    # Cache per badge
    location /badge {
        proxy_pass http://geo_app;
        proxy_cache_valid 200 1h;
        add_header X-Cache-Status \$upstream_cache_status;
    }

    # Health check
    location /health {
        proxy_pass http://geo_app;
        access_log off;
    }
}
NGINX_EOF

# Abilita sito
ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/${DOMAIN}
rm -f /etc/nginx/sites-enabled/default

# Test configurazione
if nginx -t 2>&1 | grep -q "syntax is ok"; then
    log_success "Configurazione Nginx valida"
else
    log_error "Errore nella configurazione Nginx"
    nginx -t
    exit 1
fi

# Riavvia Nginx
systemctl reload nginx
log_success "Nginx ricaricato"

# ─── Step 8: Certbot SSL ────────────────────────────────────────────────────────
log_info "Step 8: Configurazione SSL con Certbot..."

# Installazione certificato
certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN} --redirect

# Auto-rinnovo
systemctl enable certbot.timer
log_success "Certificato SSL configurato"

# ─── Step 9: Configurazione UFW firewall ────────────────────────────────────────
log_info "Step 9: Configurazione firewall UFW..."

ufw allow OpenSSH
ufw allow 'Nginx Full'  # HTTP + HTTPS
ufw --force enable
log_success "Firewall configurato"

# ─── Step 10: Systemd service ───────────────────────────────────────────────────
log_info "Step 10: Creazione systemd service..."

cat > /etc/systemd/system/geo-web.service << 'SYSTEMD_EOF'
[Unit]
Description=GEO Optimizer Web API
After=network.target nginx.service
Requires=nginx.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=ALLOWED_ORIGINS=https://${DOMAIN}
Environment=GEO_LANG=it
Environment=PORT=${APP_PORT}

# Use host networking so Uvicorn sees Nginx as a trusted local proxy.
# This keeps ProxyHeadersMiddleware effective and prevents Starlette
# directory redirects from generating http:// Location headers.
ExecStart=/usr/bin/docker run --rm \
    -e ALLOWED_ORIGINS=https://${DOMAIN} \
    -e GEO_LANG=it \
    -e PORT=${APP_PORT} \
    --network host \
    --name geo-web \
    geo-optimizer-web

# Stop command
ExecStop=/usr/bin/docker stop geo-web
ExecStop=/usr/bin/docker rm geo-web

# Restart policy
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

log_success "Systemd service creato"

# ─── Step 11: Avvio servizio ────────────────────────────────────────────────────
log_info "Step 11: Avvio servizio GEO Web..."

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable geo-web
systemctl restart geo-web
sleep 3
systemctl status geo-web --no-pager

log_success "Servizio GEO Web avviato"

# ─── Step 12: Verifica finale ───────────────────────────────────────────────────
log_info "Step 12: Verifica finale..."

# Test locale
sleep 2
if curl -sf http://localhost:${APP_PORT}/health > /dev/null; then
    log_success "API健康 check passato"
else
    log_error "API health check fallito"
    log_info "Controllare i log: journalctl -u geo-web -n 50"
fi

# Test HTTPS
if curl -sf -k "https://localhost/health" > /dev/null 2>&1; then
    log_success "HTTPS funzionante"
else
    log_info "Test HTTPS: attendere che Certbot completi..."
fi

# ─── Riepilogo ──────────────────────────────────────────────────────────────────
echo ""
log_success "=== DEPLOY COMPLETATO ==="
echo ""
echo "Endpoint disponibili:"
echo "  - Homepage:      https://${DOMAIN}/"
echo "  - API Audit:     https://${DOMAIN}/api/audit?url=..."
echo "  - Badge SVG:     https://${DOMAIN}/badge?url=..."
echo "  - Compare:       https://${DOMAIN}/compare"
echo "  - Documentazione: https://${DOMAIN}/docs/"
echo ""
echo "Comandi utili:"
echo "  - Log:           journalctl -u geo-web -f"
echo "  - Restart:       systemctl restart geo-web"
echo "  - Stato:         systemctl status geo-web"
echo ""
echo "Prossimo passo: Configura il DNS di ${DOMAIN} verso ${SERVER_IP}"
