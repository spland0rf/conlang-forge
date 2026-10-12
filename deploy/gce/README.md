# Deploying to a Google Cloud e2-micro VM (free tier)

One small VM runs everything: the app, PostgreSQL and Caddy (a web server that gets the HTTPS certificate for you).
Nightly database backups go to a Cloud Storage bucket. Nothing here uses Cloud SQL, Cloud Run or Redis.

What the visitor sees:
* `https://www.splandorf.com/` is a small static page (`site/index.html`) listing your projects. It has one entry now, a link to Conlang Forge.
  Add more `<li>` entries to that file for future projects; `update.sh` publishes it.
* `https://www.splandorf.com/conlang/` is Conlang Forge. (`https://splandorf.com/...` redirects to `www`.)

Defaults baked into `setup.sh` (override with environment variables `SITE_HOST`, `APEX`, `BUCKET`, `GOOGLE_CLIENT_ID`):
`www.splandorf.com`, `splandorf.com`, bucket `conlang-forge-backups-1`.

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
| Restore | `gcloud storage cp gs://conlang-forge-backups-1/db/FILE.sql.gz - \| gunzip \| sudo -u postgres psql conlang` (into an empty database) |

Backups keep 30 days if you set the bucket's lifecycle rule as described earlier.

## Email (confirmation and password reset)
The app emails a confirmation link when someone creates an account, and a reset link when someone clicks "Forgot your password?".
Until you set this up it runs with `MAIL_PROVIDER=console`: nothing is sent, and the message (with its link) is written to the log
(`journalctl -u conlang-forge | grep -A8 EMAIL`). That is enough for you to test; real users need real email.

**Recommended: Resend** (free: 100 mails a day, 3,000 a month, one domain). It sends over HTTPS, so it does not depend on the VM's mail ports.
1. Create an account at resend.com, then **Domains > Add domain** and enter `splandorf.com`.
2. Resend shows a few DNS records (SPF, DKIM, and sometimes a return-path/MX record). Add them where your domain's DNS is managed,
   exactly as shown, then press **Verify**. This takes minutes to a few hours. Do not remove or change any records you already have.
3. **API Keys > Create API key** with "Sending access". Copy it once.
4. On the VM: `sudo nano /etc/conlang-forge/env` and set (add the lines if your file predates email):
   ```
   PUBLIC_URL=https://www.splandorf.com/conlang
   MAIL_PROVIDER=resend
   RESEND_API_KEY=<the key>
   MAIL_FROM=Conlang Forge <noreply@splandorf.com>
   ```
   then `sudo systemctl restart conlang-forge`. (Put the key only in that file, never in chat or in git.)
5. Create a test account with an address you own and check that the confirmation mail arrives. Then try "Forgot your password?".

**Any other provider** that offers SMTP (Brevo, Mailjet, SMTP2GO, a Gmail app password): set `MAIL_PROVIDER=smtp`, `SMTP_HOST`,
`SMTP_PORT` (587 for STARTTLS, 465 with `SMTP_SECURITY=ssl`), `SMTP_USER`, `SMTP_PASSWORD` and `MAIL_FROM`. Google blocks some outbound
SMTP ports from Compute Engine, so if SMTP times out, use Resend or a provider that offers port 2525 or an HTTPS API.

Behaviour worth knowing:
* Confirmation links last 48 hours, reset links 1 hour; each works once. Asking again replaces the older link, at most once a minute.
* Using a reset link also confirms the address, signs out every device, and clears a lockout.
* Accounts made with Google, or by `create-admin`, count as confirmed.
* Admin > Settings has "Model features need a confirmed email address" (off by default). Turn it on once mail works, if you want unverified
  accounts limited to forging and reading languages.
* If sending fails the sign-up still succeeds; the error is in the log, and the user can use "Send it again" in the banner.

## Limits to expect on an e2-micro
* About 1 GB of memory and a fraction of one CPU: building a language or a full vocabulary can take noticeably longer than on a
  laptop, and several people doing it at once will queue. A 2 GB swap file is added so it does not run out of memory.
* The app is capped at 650 MB (`MemoryMax` in the service file) so a runaway request restarts the app, not the VM.
* The VM and its disk live in one zone: a zone outage or deleted disk means restoring from the nightly backup.
* Security updates: `sudo apt-get update && sudo apt-get upgrade` now and then (or install `unattended-upgrades`).

## Not tested yet
These scripts were written without access to a real VM, so the first run is the test. If a step fails, send me the last lines of
output (never keys or passwords).
