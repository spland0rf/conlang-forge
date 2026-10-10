#!/usr/bin/env bash
# Pull the latest code from GitHub and restart. Run as root:  sudo bash /opt/conlang-forge/deploy/gce/update.sh
set -euo pipefail
cd /opt/conlang-forge
sudo -u conlang git pull --ff-only
sudo -u conlang venv/bin/pip install -q -r deploy/gce/requirements.txt
install -m 644 deploy/gce/conlang-forge.service /etc/systemd/system/conlang-forge.service
install -m 755 deploy/gce/backup.sh /usr/local/bin/conlang-backup
. /etc/conlang-forge/env
mkdir -p /var/www/site && cp -r deploy/gce/site/. /var/www/site/ && chmod -R a+rX /var/www/site
sed -e "s/__HOST__/$SITE_HOST/g" -e "s/__APEX__/$APEX/g" deploy/gce/Caddyfile > /etc/caddy/Caddyfile
systemctl reload caddy || true
systemctl daemon-reload
conlang-backup || echo "(backup failed; continuing)"
systemctl restart conlang-forge
sleep 3
curl -fsS http://127.0.0.1:8000/api/health && echo
