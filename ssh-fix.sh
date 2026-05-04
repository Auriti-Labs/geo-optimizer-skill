# SSH Key Fix per rescue mode
# Esegui questo script DOPPO aver accesso al server

# Assumendo che tu abbia accesso come root o debian

# Opzione 1: Se hai accesso come root
mkdir -p /home/debian/.ssh
chmod 700 /home/debian/.ssh

# Aggiungi la tua chiave pubblica
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMiHkV4gYz5Q0yiBkNbphTVe8vnuW7e1zXBC6DsRUyU3 betintel-dev" > /home/debian/.ssh/authorized_keys
chmod 600 /home/debian/.ssh/authorized_keys
chown -R debian:debian /home/debian/.ssh

# Verifica
ls -la /home/debian/.ssh/
cat /home/debian/.ssh/authorized_keys

# Riavvia SSH
service ssh restart

# Ora prova a connetterti:
# ssh -i ~/.ssh/id_ed25519 debian@51.68.234.198


# Opzione 2: Se sei già loggato come debian
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMiHkV4gYz5Q0yiBkNbphTVe8vnuW7e1zXBC6DsRUyU3 betintel-dev" > ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
