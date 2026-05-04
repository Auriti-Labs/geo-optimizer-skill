# Deploy geo-optimizer - Script di completamento

# 1. Rimuovi config nginx precedente (se esiste)
sudo rm -f /etc/nginx/sites-available/geoready.dev /etc/nginx/sites-enabled/geoready.dev
sudo nginx -t
sudo systemctl start nginx

# 2. Genera certificato SSL con Certbot
sudo certbot certonly --webroot -w /var/www/certbot -d geoready.dev -d www.geoready.dev --non-interactive --agree-tos --email admin@geoready.dev

# 3. Crea config Nginx con SSL
cat > /etc/nginx/sites-available/geoready.dev << 'EOF'
upstream geo_app {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name geoready.dev www.geoready.dev;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name geoready.dev www.geoready.dev;

    ssl_certificate /etc/letsencrypt/live/geoready.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/geoready.dev/privkey.pem;
    ssl_protocols TLSv1.3;
    ssl_prefer_server_ciphers off;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://geo_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://geo_app;
        access_log off;
    }

    location /badge {
        proxy_pass http://geo_app;
    }
}
EOF

# 4. Abilita sito e riavvia
sudo ln -sf /etc/nginx/sites-available/geoready.dev /etc/nginx/sites-enabled/geoready.dev
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# 5. Setup auto-renewal
echo "0 0 * * * root certbot renew --quiet" | sudo tee -a /etc/crontab

echo "=== Deploy completato ==="
echo "Test: https://geoready.dev/health"
