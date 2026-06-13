"""Tests for src/emailer.py."""
from datetime import date
from unittest.mock import ANY, MagicMock, patch

import pytest

from src.emailer import email_digest


class TestEmailDigest:
    def test_sends_email_successfully(self):
        with patch("src.emailer.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            email_digest(
                "Test digest body",
                "recipient@example.com",
                smtp_host="smtp.test.com",
                smtp_port=587,
                smtp_user="user@test.com",
                smtp_password="secret",
                from_addr="from@test.com",
            )

            mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=30)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user@test.com", "secret")
            mock_server.sendmail.assert_called_once()
            args = mock_server.sendmail.call_args
            assert args[0][0] == "from@test.com"
            assert args[0][1] == ["recipient@example.com"]

            # Verify subject line format
            msg_text = args[0][2]
            today = date.today().isoformat()
            assert f"Subject: {today} Em-tech news summary" in msg_text
            # Body is base64-encoded by MIMEText; check the encoded form
            assert "VGVzdCBkaWdlc3QgYm9keQ==" in msg_text

    def test_sends_email_via_ssl_port_465(self):
        """Port 465 should use SMTP_SSL instead of STARTTLS."""
        with patch("src.emailer.smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = mock_server

            email_digest(
                "body",
                "to@example.com",
                smtp_host="smtp.whatevermail.com",
                smtp_port=465,
                smtp_user="user@whatevermail.com",
                smtp_password="authcode",
            )

            mock_smtp_ssl.assert_called_once_with(
                "smtp.whatevermail.com", 465, timeout=30, context=mock_smtp_ssl.call_args[1]["context"]
            )
            mock_server.login.assert_called_once_with("user@whatevermail.com", "authcode")
            mock_server.sendmail.assert_called_once()

    def test_raises_on_missing_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="SMTP_USER and SMTP_PASSWORD"):
                email_digest("body", "to@example.com")

    def test_uses_env_vars(self):
        """All settings read from env vars (port 587 → STARTTLS path)."""
        with (
            patch.dict("os.environ", {
                "SMTP_HOST": "mail.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "env@example.com",
                "SMTP_PASSWORD": "env-pass",
                "SMTP_FROM": "env-from@example.com",
            }),
            patch("src.emailer.smtplib.SMTP") as mock_smtp,
        ):
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            email_digest("body", "to@example.com")
            mock_smtp.assert_called_once_with("mail.example.com", 587, timeout=30)
            mock_server.login.assert_called_once_with("env@example.com", "env-pass")

    def test_subject_format(self):
        """Subject line must be: YYYY-MM-DD Em-tech news summary"""
        with patch.dict("os.environ", {}, clear=True), patch("src.emailer.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            email_digest(
                "body",
                "to@example.com",
                smtp_host="smtp.test.com",
                smtp_port=587,
                smtp_user="u",
                smtp_password="p",
                from_addr="f",
            )

            args = mock_server.sendmail.call_args
            msg = args[0][2]
            today = date.today().isoformat()
            assert f"Subject: {today} Em-tech news summary" in msg
