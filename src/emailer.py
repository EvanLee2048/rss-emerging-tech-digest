"""SMTP email delivery for the Emerging Tech Digest.

Generates a multipart/alternative MIME message with both HTML
(600px newsletter layout, inline styles, dark mode) and plain text.

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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import Optional

from src.types import Article

logger = logging.getLogger(__name__)


# HTML template parts

_HTML_HEADER = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-media" content="light dark">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Emerging Tech Digest</title>
  <style type="text/css">
    @media (prefers-color-scheme: dark) {
      .dark-bg   { background-color: #1a1d2e !important; }
      .dark-card { background-color: #252840 !important; }
      .dark-text { color: #e0e0e0 !important; }
      .dark-head { color: #ffffff !important; }
      .dark-border { border-left-color: #f45b4f !important; }
      .dark-sep  { border-bottom-color: #3a3d5c !important; }
      .dark-muted { color: #9999b3 !important; }
    }
  </style>
</head>
<body style="margin:0;padding:0;background-color:#f0f2f8;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f2f8;" class="dark-bg">
<tr><td align="center" style="padding:20px 10px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:8px;overflow:hidden;" class="dark-card">
"""

_HTML_FOOTER = """\
</td></tr>
<!-- Footer -->
<tr><td style="padding:20px 30px;background-color:#f8f9fc;border-top:1px solid #e0e4ed;" class="dark-card dark-sep">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#9999b3;line-height:16px;" class="dark-muted">
        Emerging Tech Digest &middot; Automated intelligence briefing<br>
        Sent %s
      </td>
      <td align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:11px;">
        <a href="{{UNSUBSCRIBE}}" style="color:#9999b3;text-decoration:underline;" class="dark-muted">Unsubscribe</a>
      </td>
    </tr>
  </table>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _render_article_html(a: Article, index: int) -> str:
    """Render a single article as an HTML table row block."""
    date_str = (
        '<span style="color:#9999b3;font-size:12px;" class="dark-muted">'
        + a.date
        + "</span>"
    ) if a.date else ""

    bullets_html = ""
    if a.bullets:
        for line in a.bullets.split("\n"):
            line = line.strip().lstrip("- ")
            if line:
                bullets_html += (
                    '<tr><td style="padding:2px 0;font-family:Arial,Helvetica,'
                    'sans-serif;font-size:14px;color:#444;line-height:1.5;" '
                    'class="dark-text">&#8226; '
                    + line + "</td></tr>\n"
                )

    briefing_html = ""
    if a.director_briefing:
        for line in a.director_briefing.split("\n"):
            line = line.strip().lstrip("- ")
            if line:
                if ":**" in line:
                    parts = line.split(":**", 1)
                    label = parts[0].lstrip("*").strip()
                    rest = parts[1]
                    briefing_html += (
                        '<tr><td style="padding:2px 0;font-family:Arial,Helvetica,'
                        'sans-serif;font-size:13px;color:#555;line-height:1.5;" '
                        'class="dark-text">'
                        '<strong style="color:#333;" class="dark-head">'
                        + label
                        + ':</strong>'
                        + rest
                        + "</td></tr>\n"
                    )
                else:
                    briefing_html += (
                        '<tr><td style="padding:2px 0;font-family:Arial,Helvetica,'
                        'sans-serif;font-size:13px;color:#555;line-height:1.5;" '
                        'class="dark-text">'
                        + line
                        + "</td></tr>\n"
                    )

    return (
        '<!-- Article ' + str(index) + ' -->\n'
        '<tr><td style="padding:20px 30px 10px 30px;">\n'
        '  <table width="100%" cellpadding="0" cellspacing="0">\n'
        '    <tr>\n'
        '      <td style="border-left:4px solid #f45b4f;padding-left:16px;" class="dark-border">\n'
        '        <table width="100%" cellpadding="0" cellspacing="0">\n'
        '          <tr><td style="font-family:Arial,Helvetica,sans-serif;'
        'font-size:11px;color:#9999b3;padding-bottom:4px;" class="dark-muted">'
        + a.feed_label
        + (" &middot; " + a.date if a.date else "")
        + '</td></tr>\n'
        '          <tr><td style="font-family:Arial,Helvetica,sans-serif;'
        'font-size:17px;font-weight:bold;color:#1a1d2e;padding-bottom:8px;" class="dark-head">\n'
        '            <a href="' + a.url + '" style="color:#1a1d2e;text-decoration:none;" class="dark-head">'
        + a.title + '</a>\n'
        '          </td></tr>\n'
        '        </table>\n'
        '      </td>\n'
        '    </tr>\n'
        '  </table>\n'
        '</td></tr>\n'
        '<tr><td style="padding:0 30px 0 50px;">\n'
        '  <table width="100%" cellpadding="0" cellspacing="0">\n'
        + bullets_html
        + '  </table>\n'
        '</td></tr>\n'
        + (  # Wrapped Consulting Insight box
            '<tr><td style="padding:8px 30px 5px 50px;">\n'
            '  <table width="100%" cellpadding="0" cellspacing="0">\n'
            '    <tr><td style="background-color:#f8f6ff;border:1px solid #e0d8f0;'
            'border-radius:6px;padding:12px 16px;" class="dark-card">\n'
            '      <table width="100%" cellpadding="0" cellspacing="0">\n'
            '        <tr><td style="font-family:Arial,Helvetica,sans-serif;'
            'font-size:11px;font-weight:bold;color:#7c5cbf;text-transform:uppercase;'
            'letter-spacing:1px;padding-bottom:6px;" class="dark-head">\n'
            '          Consulting Insight\n'
            '        </td></tr>\n'
            + briefing_html
            + '      </table>\n'
            '    </td></tr>\n'
            '  </table>\n'
            '</td></tr>\n'
        ) if briefing_html else ''
        + '<tr><td style="padding:0 30px 10px 50px;">\n'
        '  <table width="100%" cellpadding="0" cellspacing="0">\n'
        '    <tr><td style="border-bottom:1px solid #e0e4ed;height:1px;" class="dark-sep"></td></tr>\n'
        '  </table>\n'
        '</td></tr>\n'
    )


def render_html_digest(
    articles: list[Article],
    feeds_scanned: int,
    categories_with_new: list[str],
) -> str:
    """Generate a full HTML newsletter from article data.

    Args:
        articles: Processed articles with bullets, briefing populated.
        feeds_scanned: Number of feeds scanned.
        categories_with_new: Category labels with new content.

    Returns:
        Complete HTML string (inline styles, dark mode, 600px layout).
    """
    today_str = date.today().strftime("%B %d, %Y")
    body = ""

    # Header area
    body += (
        '<tr><td style="padding:30px 30px 10px 30px;'
        'background:linear-gradient(135deg,#0f1528,#1a1d2e);">\n'
        '  <table width="100%" cellpadding="0" cellspacing="0">\n'
        '    <tr>\n'
        '      <td style="font-family:Arial,Helvetica,sans-serif;'
        'font-size:22px;font-weight:bold;color:#ffffff;padding-bottom:4px;">\n'
        '        Emerging Tech Digest\n'
        '      </td>\n'
        '    </tr>\n'
        '    <tr>\n'
        '      <td style="font-family:Arial,Helvetica,sans-serif;'
        'font-size:13px;color:#9999b3;">\n'
        + today_str + " &middot; " + str(feeds_scanned) + " sources\n"
        + '      </td>\n'
        '    </tr>\n'
        '  </table>\n'
        '</td></tr>\n'
        '<tr><td style="padding:0 30px 20px 30px;'
        'background:linear-gradient(135deg,#0f1528,#1a1d2e);">\n'
        '  <table width="100%" cellpadding="0" cellspacing="0">\n'
        '    <tr><td style="border-top:1px solid #f45b4f;height:1px;"></td></tr>\n'
        '  </table>\n'
        '</td></tr>\n'
    )

    if categories_with_new:
        cat_str = ", ".join(categories_with_new)
        body += (
            '<tr><td style="padding:0 30px 15px 30px;">\n'
            '  <table width="100%" cellpadding="0" cellspacing="0">\n'
            '    <tr><td style="font-family:Arial,Helvetica,sans-serif;'
            'font-size:13px;color:#888;font-style:italic;" class="dark-muted">\n'
            '      New articles in: ' + cat_str + '\n'
            '    </td></tr>\n'
            '  </table>\n'
            '</td></tr>\n'
        )

    for i, article in enumerate(articles):
        body += _render_article_html(article, i + 1)

    return _HTML_HEADER + body + _HTML_FOOTER.replace("%s", today_str)


def render_plain_text(
    articles: list[Article],
    feeds_scanned: int,
    categories_with_new: list[str],
) -> str:
    """Generate a plain-text version of the digest."""
    lines = []
    lines.append("Emerging Tech Digest - " + date.today().isoformat())
    lines.append("Sourced from " + str(feeds_scanned) + " feeds")
    if categories_with_new:
        lines.append("New articles in: " + ", ".join(sorted(categories_with_new)))
    lines.append("")

    for i, article in enumerate(articles):
        lines.append("[" + str(i + 1) + "] " + article.title)
        date_str = " | " + article.date if article.date else ""
        lines.append("    " + article.feed_label + date_str)
        lines.append("    " + article.url)
        if article.bullets:
            for line in article.bullets.split("\n"):
                line = line.strip()
                if line:
                    lines.append("    " + line)
        if article.director_briefing:
            for line in article.director_briefing.split("\n"):
                line = line.strip()
                if line:
                    lines.append("    " + line)
        lines.append("")

    return "\n".join(lines)


# SMTP sending


def _env_or(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def email_digest(
    digest_text: str,
    to_addr: str,
    articles: Optional[list[Article]] = None,
    feeds_scanned: int = 0,
    categories_with_new: Optional[list[str]] = None,
    *,
    smtp_host: str = "",
    smtp_port: int = 0,
    smtp_user: str = "",
    smtp_password: str = "",
    from_addr: str = "",
) -> None:
    """Send the digest as a multipart/alternative email (HTML + plain text).

    Args:
        digest_text: Plain text digest (fallback body).
        to_addr: Recipient email address.
        articles: Article data for generating HTML version.
        feeds_scanned: Number of feeds scanned.
        categories_with_new: Categories with new content.
        smtp_host: SMTP server hostname (default from SMTP_HOST env).
        smtp_port: SMTP server port (default from SMTP_PORT env).
        smtp_user: SMTP username (default from SMTP_USER env).
        smtp_password: SMTP password (default from SMTP_PASSWORD env).
        from_addr: From address (default from SMTP_FROM, falls back to SMTP_USER).
    """
    smtp_host = smtp_host or _env_or("SMTP_HOST", "smtp.gmail.com")
    smtp_port = smtp_port or int(_env_or("SMTP_PORT", "587"))
    smtp_user = smtp_user or _env_or("SMTP_USER", "")
    smtp_password = smtp_password or _env_or("SMTP_PASSWORD", "")
    from_addr = from_addr or _env_or("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        raise ValueError(
            "SMTP_USER and SMTP_PASSWORD must be set via config.yaml "
            "or function arguments"
        )

    today = date.today()
    subject = today.isoformat() + " Em-tech news summary"

    # Build multipart/alternative message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Date"] = formatdate(localtime=True)

    # Plain text part
    msg.attach(MIMEText(digest_text, "plain", "utf-8"))

    # HTML part (if article data provided)
    if articles:
        html = render_html_digest(
            articles,
            feeds_scanned=feeds_scanned,
            categories_with_new=categories_with_new or [],
        )
        msg.attach(MIMEText(html, "html", "utf-8"))

    context = ssl.create_default_context()
    smtp_port = int(smtp_port)
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, [to_addr], msg.as_string())

    logger.info("Digest emailed to %s (subject: %s)", to_addr, subject)
