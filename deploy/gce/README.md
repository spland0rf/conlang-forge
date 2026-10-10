# Deploying to a Google Cloud e2-micro VM (free tier)

One small VM runs everything: the app, PostgreSQL and Caddy (a web server that gets the HTTPS certificate for you).
Nightly database backups go to a Cloud Storage bucket. Nothing here uses Cloud SQL, Cloud Run or Redis.

What the visitor sees:
* `https://www.splandorf.com/` is a small static page (`site/index.html`) listing your projects. It has one entry now, a link to Conlang Forge.
  Add more `<li>` entries to that file for future projects; `update.sh` publishes it.
* `https://www.splandorf.com/conlang/` is Conlang Forge. (`https://splandorf.com/...` redirects to `www`.)

Defaults baked into `setup.sh` (override with environment variables `SITE_HOST`, `APEX`, `BUCKET`, `GOOGLE_CLIENT_ID`):
`www.splandorf.com`, `splandorf.com`, bucket `conlang-forge-backup-1`.

## Before you run anything
1. **DNS:** at your domain registrar add two `A` records pointing at the VM's static IP: `www` (so `www.splandorf.com`) and `@` (the bare
   `splandorf.com`, which redirects to `www`). Check with `nslookup www.splandorf.com`. If the domain already points elsewhere, change it
   only when you are ready, because this replaces whatever is served there now.
2. **VM permissions:** the VM's service account must be allowed to *write* to Cloud Storage. In the console, Compute Engine -> VM
   instances -> your VM -> Stop -> Edit -> *Access scopes* -> choose "Set access for each API" and set **Storage** to
   **Read Write** (or pick "Allow full access to all Cloud APIs") -> Save -> Start. (The default "Storage: Read Only" makes
   backups fail.) The service account also needs the *Storage Object Admin* role on the bucket.
3. **Google sign-in:** APIs & Services -> Credentials -> your OAuth client -> Authorized JavaScript origins must contain
   `https://www.splandorf.com` (no path, no trailing slash). Changes can take a few minutes to apply.
4. **Merge the pull request** that added this folder, so the code is on `main`.

## Install (about 10 minutes)
Open the VM's **SSH** button in the console, then:

```bash
# 1. a read-only key so the VM can download the (private) repository
sudo apt-get update -qq && sudo apt-get install -y -qq git
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 && cat ~/.ssh/id_ed25519.pub
```
Copy the line it prints. On GitHub: repository -> Settings -> Deploy keys -> Add deploy key -> paste it, leave
"Allow write access" **off**. Then back in the SSH window:

```bash
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null
git clone -b main git@github.com:spland0rf/conlang-forge.git ~/conlang-forge
sudo bash ~/conlang-forge/deploy/gce/setup.sh
```
The script asks for your Anthropic API key (hidden; Enter skips it) and for the administrator email and password. It
installs everything, starts the app and prints a health check. Then open `https://www.splandorf.com/` and follow the link.

## Day to day
| What | Command |
|---|---|
| Logs | `journalctl -u conlang-forge -f` |
| Update to the latest `main` | `sudo bash /opt/conlang-forge/deploy/gce/update.sh` |
| Back up now | `sudo conlang-backup` |
| Change a setting or key | `sudo nano /etc/conlang-forge/env` then `sudo systemctl restart conlang-forge` |
| Restore | `gcloud storage cp gs://conlang-forge-backup-1/db/FILE.sql.gz - \| gunzip \| sudo -u postgres psql conlang` (into an empty database) |

Backups keep 30 days if you set the bucket's lifecycle rule as described earlier.

## Limits to expect on an e2-micro
* About 1 GB of memory and a fraction of one CPU: building a language or a full vocabulary can take noticeably longer than on a
  laptop, and several people doing it at once will queue. A 2 GB swap file is added so it does not run out of memory.
* The app is capped at 650 MB (`MemoryMax` in the service file) so a runaway request restarts the app, not the VM.
* The VM and its disk live in one zone: a zone outage or deleted disk means restoring from the nightly backup.
* Security updates: `sudo apt-get update && sudo apt-get upgrade` now and then (or install `unattended-upgrades`).

## Not tested yet
These scripts were written without access to a real VM, so the first run is the test. If a step fails, send me the last lines of
output (never keys or passwords).
