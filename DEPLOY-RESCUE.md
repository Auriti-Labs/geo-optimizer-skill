# Deploy su server in Rescue Mode

Se il server è in rescue mode, segui questa guida:

## Passo 1: Accedi in rescue mode

```bash
ssh debian@51.68.234.198
# oppure usa la console web del provider (Vultr/Contabo/DigitalOcean)
```

## Passo 2: Verifica configurazione di rete

```bash
ip a show
ip route show
cat /etc/resolv.conf
```

Se manca il gateway o DNS, configurane uno:

```bash
# Esempio per Debian
auto eth0
iface eth0 inet static
    address 51.68.234.198/24
    gateway 51.68.234.1
    dns-nameservers 8.8.8.8 1.1.1.1
```

## Passo 3: Installazione base (in rescue mode)

In rescue mode, monta il filesystem principale:

```bash
# Monta il disco principale
mount /dev/sda1 /mnt

# Se hai partitioni separate, montale anch'esse
mount /dev/sda2 /mnt/home 2>/dev/null || true
mount /dev/sda3 /mnt/var 2>/dev/null || true

# Bind mount per chroot
mount --bind /dev /mnt/dev
mount --bind /proc /mnt/proc
mount --bind /sys /mnt/sys
mount --bind /run /mnt/run
```

## Passo 4: Chroot e installazione

```bash
# Chroot nel sistema principale
chroot /mnt /bin/bash

# Ora sei nel sistema principale
# Installa SSH server
apt update
apt install -y openssh-server

# Configura SSH
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Abilita SSH al boot
systemctl enable ssh

# Riavviare SSH
service ssh restart

# Esci dal chroot
exit

# Smonta i filesystem
umount /mnt/dev /mnt/proc /mnt/sys /mnt/run /mnt/home /mnt/var /mnt
```

## Passo 5: Riavvio normale

Ora riavvia la macchina normalmente (dalla console del provider o con `reboot`):

```bash
reboot
```

## Passo 6: Dopo il riavvio

Una volta rientrato in SSH:

```bash
ssh debian@51.68.234.198

# Verifica SSH
systemctl status ssh

# Installa Docker
curl -sSL https://get.docker.com | sh
usermod -aG docker debian

# Installa Docker Compose
curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

## Passo 7: Esegui lo script di deploy

```bash
cd /tmp
wget https://raw.githubusercontent.com/Auriti-Labs/geo-optimizer-skill/main/deploy-geoready.sh
chmod +x deploy-geoready.sh
bash deploy-geoready.sh
```

---

## Configurazione Firewall (Importante!)

Dopo il deploy, assicurati che il firewall non blocchi le porte necessarie:

```bash
# Abilita UFW e apri porte
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Verifica
ufw status verbose
```

Output atteso:
```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
Nginx Full                 ALLOW       Anywhere
OpenSSH (v6)               ALLOW       Anywhere (v6)
Nginx Full (v6)            ALLOW       Anywhere (v6)
```

---

## Risoluzione problemi comuni

### SSH non parte
```bash
# Log di SSH
journalctl -u ssh -f

# Verifica config
sshd -t
```

### Docker non funziona
```bash
# Log di Docker
journalctl -u docker -f
docker info
```

### Nginx non parte
```bash
nginx -t  # Verifica config
journalctl -u nginx -f
```

### Certbot SSL non funziona
```bash
# Verifica porta 80 e 443
ufw status
netstat -tlnp | grep -E ':80|:443'
```

---

## Verifica finale

Dopo tutto il deploy:

```bash
# Verifica i servizi
systemctl status geo-web
systemctl status nginx
systemctl status docker

# Test l'app
curl https://geoready.dev/
curl https://geoready.dev/health
curl https://geoready.dev/robots.txt
curl https://geoready.dev/llms.txt

# Verifica SSL
openssl s_client -connect geoready.dev:443 -servername geoready.dev < /dev/null | openssl x509 -noout -dates
```
