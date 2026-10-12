"""Sending email. Four interchangeable senders; MAIL_PROVIDER picks one.

* resend   HTTPS API (api.resend.com). Needs RESEND_API_KEY. Free tier: 100 mails a day. Works where SMTP ports are blocked.
* smtp     any SMTP server (Brevo, Mailjet, SMTP2GO, Gmail app password ...). SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
           SMTP_SECURITY = starttls (default, port 587) | ssl (port 465) | none.
* console  writes the message to the server log instead of sending it (development, or before mail is set up).
* fake     keeps messages in memory (tests).

MAIL_FROM is the sender, e.g. "Conlang Forge <noreply@splandorf.com>". send() raises MailError when delivery fails;
callers decide whether that matters.
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import parseaddr

log = logging.getLogger("conlang_forge.mail")


class MailError(Exception):
    pass


@dataclass
class Mail:
    to: str
    subject: str
    text: str


class Mailer:
    name = "base"
    sender = "Conlang Forge <noreply@localhost>"

    def send(self, mail: Mail) -> None:
        raise NotImplementedError


class ConsoleMailer(Mailer):
    name = "console"

    def __init__(self, sender: str = Mailer.sender):
        self.sender = sender

    def send(self, mail: Mail) -> None:
        log.warning("EMAIL (not sent; MAIL_PROVIDER=console)\nTo: %s\nSubject: %s\n\n%s", mail.to, mail.subject, mail.text)


class FakeMailer(Mailer):
    name = "fake"

    def __init__(self, sender: str = Mailer.sender):
        self.sender, self.sent, self.fail = sender, [], False

    def send(self, mail: Mail) -> None:
        if self.fail:
            raise MailError("simulated delivery failure")
        self.sent.append(mail)


class ResendMailer(Mailer):
    name = "resend"
    URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, sender: str, timeout: float = 15):
        if not api_key:
            raise ValueError("RESEND_API_KEY is not set")
        self.key, self.sender, self.timeout = api_key, sender, timeout

    def send(self, mail: Mail) -> None:
        body = json.dumps({"from": self.sender, "to": [mail.to], "subject": mail.subject, "text": mail.text}).encode()
        req = urllib.request.Request(self.URL, data=body, method="POST", headers={
            "Authorization": f"Bearer {self.key}", "Content-Type": "application/json", "User-Agent": "conlang-forge/1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                r.read()
        except urllib.error.HTTPError as e:
            raise MailError(f"Resend answered {e.code}: {e.read(300).decode('utf-8', 'replace')}") from None
        except Exception as e:
            raise MailError(f"could not reach Resend: {e}") from None


class SmtpMailer(Mailer):
    name = "smtp"

    def __init__(self, host: str, port: int, user: str, password: str, sender: str, security: str = "starttls",
                 timeout: float = 15):
        if not host:
            raise ValueError("SMTP_HOST is not set")
        self.host, self.port, self.user, self.password = host, port, user, password
        self.sender, self.security, self.timeout = sender, security, timeout

    def send(self, mail: Mail) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, mail.to, mail.subject
        msg.set_content(mail.text)
        try:
            ctx = ssl.create_default_context()
            if self.security == "ssl":
                s = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=ctx)
            else:
                s = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            with s:
                if self.security == "starttls":
                    s.starttls(context=ctx)
                if self.user:
                    s.login(self.user, self.password)
                s.send_message(msg, from_addr=parseaddr(self.sender)[1] or self.sender)
        except Exception as e:
            raise MailError(f"SMTP delivery failed: {e}") from None


def mailer_from_env(env=None) -> Mailer:
    env = os.environ if env is None else env
    kind = (env.get("MAIL_PROVIDER") or "console").strip().lower()
    sender = env.get("MAIL_FROM") or Mailer.sender
    if kind == "resend":
        return ResendMailer(env.get("RESEND_API_KEY", ""), sender)
    if kind == "smtp":
        security = (env.get("SMTP_SECURITY") or "starttls").lower()
        port = int(env.get("SMTP_PORT") or (465 if security == "ssl" else 587))
        return SmtpMailer(env.get("SMTP_HOST", ""), port, env.get("SMTP_USER", ""), env.get("SMTP_PASSWORD", ""),
                          sender, security)
    if kind == "console":
        return ConsoleMailer(sender)
    if kind == "fake":
        return FakeMailer(sender)
    raise ValueError(f"unknown MAIL_PROVIDER {kind!r} (use resend, smtp or console)")


# ---------------------------------------------------------------- the messages
def verification_mail(to: str, name: str, link: str) -> Mail:
    return Mail(to, "Confirm your email for Conlang Forge",
                f"Hi {name},\n\nConfirm your email address to finish setting up your Conlang Forge account:\n\n{link}\n\n"
                "The link works for 48 hours. If you did not create this account, you can ignore this message.\n")


def reset_mail(to: str, name: str, link: str) -> Mail:
    return Mail(to, "Reset your Conlang Forge password",
                f"Hi {name},\n\nSomeone asked to reset the password for this account. To choose a new password, open:\n\n{link}\n\n"
                "The link works for one hour and only once. If you did not ask for this, ignore this message; your password has not changed.\n")
