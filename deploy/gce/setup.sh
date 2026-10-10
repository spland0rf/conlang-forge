#!/usr/bin/env bash
# One-time setup of Conlang Forge on a Debian 12 Compute Engine VM (an e2-micro is enough).
# Run as root:   sudo bash deploy/gce/setup.sh
# Safe to re-run: it skips what is already done and never overwrites your settings file.
set -euo pipefail

REPO_SSH="git@github.com:spland0rf/conlang-forge.git"
APP_DIR=/opt/conlang-forge
ENV_DIR=/etc/conlang-forge
ENV_FILE=$ENV_DIR/env
DOMAIN="${DOMAIN:-splandorf.com}"
BUCKET="${BUCKET:-conlang-forge-backup-1}"
GOOGLE_CLIENT_ID_DEFAULT="${GOOGLE_CLIENT_ID:-961218891902-9puiota448g8fqma2m2jj53ocmhjrcai.apps.googleusercontent.com}"

[ "$(id -u)" = 0 ] || { echo "Run this as root: sudo bash $0"; exit 1; }
say() { printf '\n==> %s\n' "$*"; }

say "1/8 Packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git postgresql caddy curl >/dev/null

say "2/8 Swap file (the e2-micro has only 1 GB of memory)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo 'vm.swappiness=20' > /etc/sysctl.d/90-conlang.conf && sysctl -q --system
fi

say "3/8 App user and code"
id conlang >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash conlang
KEY=/home/conlang/.ssh/id_ed25519
if [ ! -f "$KEY" ]; then
  sudo -u conlang mkdir -p -m 700 /home/conlang/.ssh
  LOGIN_HOME=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)
  if [ -f "$LOGIN_HOME/.ssh/id_ed25519" ]; then       # reuse the deploy key you set up to download this script
    install -o conlang -g conlang -m 600 "$LOGIN_HOME/.ssh/id_ed25519" "$KEY"
    install -o conlang -g conlang -m 644 "$LOGIN_HOME/.ssh/id_ed25519.pub" "$KEY.pub"
  else
    sudo -u conlang ssh-keygen -q -t ed25519 -N "" -C "conlang-forge-vm" -f "$KEY"
  fi
  sudo -u conlang sh -c 'ssh-keyscan -t ed25519 github.com >> /home/conlang/.ssh/known_hosts 2>/dev/null'
fi
if [ ! -d "$APP_DIR/.git" ]; then
  if ! sudo -u conlang git ls-remote "$REPO_SSH" >/dev/null 2>&1; then
    cat <<MSG

  The VM cannot read the GitHub repository yet. Add this public key as a READ-ONLY deploy key:
    GitHub -> spland0rf/conlang-forge -> Settings -> Deploy keys -> Add deploy key (leave "Allow write access" OFF)

$(cat "$KEY.pub")

  Then run this script again.
MSG
    exit 2
  fi
  mkdir -p "$APP_DIR" && chown conlang:conlang "$APP_DIR"
  sudo -u conlang git clone -q "$REPO_SSH" "$APP_DIR"
fi
cd "$APP_DIR"
sudo -u conlang python3 -m venv venv
sudo -u conlang venv/bin/pip install -q --upgrade pip
sudo -u conlang venv/bin/pip install -q -r deploy/gce/requirements.txt

say "4/8 PostgreSQL (kept small for 1 GB of memory; listens on this machine only)"
cat > "$(ls -d /etc/postgresql/*/main/conf.d | head -1)/conlang.conf" <<'CONF'
listen_addresses = 'localhost'
max_connections = 30
shared_buffers = 64MB
work_mem = 4MB
maintenance_work_mem = 32MB
effective_cache_size = 256MB
CONF
systemctl restart postgresql
mkdir -p "$ENV_DIR" && chmod 750 "$ENV_DIR" && chown root:conlang "$ENV_DIR"
if [ ! -f "$ENV_FILE" ]; then
  DBPASS=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')
  SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
  sudo -u postgres psql -qc "CREATE ROLE conlang LOGIN PASSWORD '$DBPASS'"
  sudo -u postgres psql -qc "CREATE DATABASE conlang OWNER conlang"
  cat > "$ENV_FILE" <<ENVF
DATABASE_URL=postgresql://conlang:$DBPASS@127.0.0.1:5432/conlang
CONLANG_FORGE_SECRET=$SECRET
GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID_DEFAULT
ANTHROPIC_API_KEY=
CONLANG_DB_POOL=6
DOMAIN=$DOMAIN
BUCKET=$BUCKET
ENVF
  chmod 640 "$ENV_FILE" && chown root:conlang "$ENV_FILE"
fi
set -a; . "$ENV_FILE"; set +a

say "5/8 Anthropic API key (the model-powered features need it; press Enter to skip for now)"
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -t 0 ]; then
  read -r -s -p "Paste your Anthropic API key (input hidden): " KEYIN; echo
  if [ -n "$KEYIN" ]; then sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$KEYIN|" "$ENV_FILE"; fi
fi

say "6/8 Administrator account"
HAS_ADMIN=$(sudo -u postgres psql -Atqd conlang -c "SELECT CASE WHEN to_regclass('public.users') IS NULL THEN 0 ELSE (SELECT COUNT(*) FROM users WHERE role='admin') END")
if [ "$HAS_ADMIN" = 0 ] && [ -t 0 ]; then
  read -r -p "Administrator email: " ADMIN_EMAIL
  sudo -u conlang env $(grep -v '^$' "$ENV_FILE" | xargs) venv/bin/python -m conlang_forge create-admin --email "$ADMIN_EMAIL"
fi

say "7/8 Services (app, web server with automatic HTTPS, nightly backup)"
install -m 644 deploy/gce/conlang-forge.service /etc/systemd/system/conlang-forge.service
install -m 755 deploy/gce/backup.sh /usr/local/bin/conlang-backup
install -m 644 deploy/gce/conlang-backup.service /etc/systemd/system/conlang-backup.service
install -m 644 deploy/gce/conlang-backup.timer /etc/systemd/system/conlang-backup.timer
sed "s/__DOMAIN__/$DOMAIN/g" deploy/gce/Caddyfile > /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now conlang-forge conlang-backup.timer
systemctl reload caddy || systemctl restart caddy

say "8/8 Check"
sleep 4
curl -fsS http://127.0.0.1:8000/api/health && echo
systemctl --no-pager --lines=0 status conlang-forge | head -3
cat <<DONE

Done. Open https://$DOMAIN once your DNS record points at this VM's static IP
(the first visit may take a few seconds while the HTTPS certificate is issued).
  Logs:      journalctl -u conlang-forge -f
  Update:    sudo bash $APP_DIR/deploy/gce/update.sh
  Backup:    sudo conlang-backup      (also runs nightly)
DONE
