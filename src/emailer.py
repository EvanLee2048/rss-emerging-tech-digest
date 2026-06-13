"""SMTP email delivery for the Emerging Tech Digest.

Uses Python's built-in `smtplib` — no external dependencies.
Configured via environment variables.

Environment variables:
    SMTP_HOST       SMTP server hostname (default: smtp.gmail.com)
    SMTP_PORT       SMTP server port (default: 587)
    SMTP_USER       SMTP username (usually your email address)
    SMTP_PASSWORD   SMTP password or app password
    SMTP_FROM       From address (defaults to SMTP_USER if not set)
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from datetime import date
from email.mime.text import MIMEText
from email.utils import formatdate

logger = logging.getLogger(__name__)


def _env_or(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def email_digest(
    digest_text: str,
    to_addr: str,
    *,
    smtp_host: str = "",
    smtp_port: int = 0,
    smtp_user: str = "",
    smtp_password: str = "",
    from_addr: str = "",
) -> None:
    """Send the digest as an email via SMTP.

    Args:
        digest_text: The full digest text to send.
        to_addr: Recipient email address.
        smtp_host: SMTP server hostname (default from SMTP_HOST env).
        smtp_port: SMTP server port (default from SMTP_PORT env).
        smtp_user: SMTP username (default from SMTP_USER env).
        smtp_password: SMTP password (default from SMTP_PASSWORD env).
        from_addr: From address (default from SMTP_FROM, falls back to SMTP_USER).

    Raises:
        ValueError: If required SMTP config is missing.
        smtplib.SMTPException: On SMTP delivery failure.
    """
    smtp_host = smtp_host or _env_or("SMTP_HOST", "smtp.gmail.com")
    smtp_port = smtp_port or int(_env_or("SMTP_PORT", "587"))
    smtp_user = smtp_user or _env_or("SMTP_USER", "")
    smtp_password = smtp_password or _env_or("SMTP_PASSWORD", "")
    from_addr = from_addr or _env_or("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        raise ValueError(
            "SMTP_USER and SMTP_PASSWORD must be set via environment variables "
            "or function arguments"
        )

    today = date.today()
    subject = f"{today.isoformat()} Em-tech news summary"

    msg = MIMEText(digest_text, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Date"] = formatdate(localtime=True)

    context = ssl.create_default_context()

    smtp_port = int(smtp_port)
    if smtp_port == 465:
        # SSL (e.g., whatevermail.com, QQmail)
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
    else:
        # STARTTLS (port 587 or 25)
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, [to_addr], msg.as_string())

    logger.info("Digest emailed to %s (subject: %s)", to_addr, subject)
