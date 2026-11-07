#!/usr/bin/env bash
# Pull the latest code from GitHub and restart. Run as root:  sudo bash /opt/conlang-forge/deploy/gce/update.sh
set -euo pipefail
cd /opt/conlang-forge
sudo -u conlang git pull --ff-only
sudo -u conlang venv/bin/pip install -q -r deploy/gce/requirements.txt
install -m 644 deploy/gce/conlang-forge.service /etc/systemd/system/conlang-forge.service
install -m 755 deploy/gce/backup.sh /usr/local/bin/conlang-backup
. /etc/conlang-forge/env
# The homepage and the web-server routing for all of www.splandorf.com (every project, not just /conlang) live in the
# spland0rf/splandorf-site repository. Once its install.sh has run on this VM (it creates /etc/splandorf-site/env),
# leave them alone: overwriting them here would drop other routes. The copies here are only for a
# brand-new VM before splandorf-site is installed.
if [ ! -f /etc/splandorf-site/env ]; then
  mkdir -p /var/www/site && cp -r deploy/gce/site/. /var/www/site/ && chmod -R a+rX /var/www/site
  sed -e "s/__HOST__/$SITE_HOST/g" -e "s/__APEX__/$APEX/g" deploy/gce/Caddyfile > /etc/caddy/Caddyfile
  systemctl reload caddy || true
fi
systemctl daemon-reload
conlang-backup || echo "(backup failed; continuing)"
systemctl restart conlang-forge
sleep 3
curl -fsS http://127.0.0.1:8000/api/health && echo
