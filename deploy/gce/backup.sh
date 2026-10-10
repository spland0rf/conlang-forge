#!/usr/bin/env bash
# Nightly database backup to the Cloud Storage bucket. Uses the VM's own service account (no key files).
# Restore:  gcloud storage cp gs://BUCKET/FILE.sql.gz - | gunzip | sudo -u postgres psql conlang   (into an EMPTY database)
set -euo pipefail
. /etc/conlang-forge/env
STAMP=$(date -u +%Y-%m-%dT%H%MZ)
TMP=$(mktemp /tmp/conlang-backup.XXXXXX.sql.gz)
trap 'rm -f "$TMP"' EXIT
sudo -u postgres pg_dump --no-owner conlang | gzip -9 > "$TMP"
gcloud storage cp --quiet "$TMP" "gs://$BUCKET/db/conlang-$STAMP.sql.gz"
echo "backed up to gs://$BUCKET/db/conlang-$STAMP.sql.gz ($(du -h "$TMP" | cut -f1))"
