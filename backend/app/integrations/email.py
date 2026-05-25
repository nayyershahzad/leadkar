"""SMTP email sending + delivery template (CLAUDE.md §4, Phase 4)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings


class Mailer:
    """Sync SMTP sender (used from the Celery deliver task)."""

    def send(self, *, to: str, subject: str, html: str, text: str) -> None:
        msg = EmailMessage()
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)


def build_delivery_email(
    *, customer_name: str, pack_title: str, csv_url: str, xlsx_url: str, ttl_hours: int
) -> tuple[str, str, str]:
    """Return (subject, html, text) for a catalog-order delivery."""
    subject = f"Your LeadKar leads are ready — {pack_title}"
    text = (
        f"Hi {customer_name},\n\n"
        f"Your LeadKar pack \"{pack_title}\" is ready. Download your leads:\n\n"
        f"CSV:  {csv_url}\n"
        f"XLSX: {xlsx_url}\n\n"
        f"These links expire in {ttl_hours} hours.\n\n"
        f"Thank you for choosing LeadKar.\n"
    )
    html = f"""\
<!doctype html>
<html>
  <body style="margin:0;background:#f4f5f7;font-family:Arial,Helvetica,sans-serif;color:#1a1a1a;">
    <div style="max-width:560px;margin:0 auto;padding:32px 24px;">
      <h1 style="color:#0b5fff;font-size:22px;margin:0 0 8px;">LeadKar</h1>
      <p style="font-size:15px;">Hi {customer_name},</p>
      <p style="font-size:15px;">Your pack <strong>{pack_title}</strong> is ready. Download your verified leads below:</p>
      <p style="margin:24px 0;">
        <a href="{csv_url}" style="display:inline-block;background:#0b5fff;color:#fff;text-decoration:none;padding:12px 20px;border-radius:6px;font-size:15px;margin-right:8px;">Download CSV</a>
        <a href="{xlsx_url}" style="display:inline-block;background:#0b5fff;color:#fff;text-decoration:none;padding:12px 20px;border-radius:6px;font-size:15px;">Download XLSX</a>
      </p>
      <p style="font-size:13px;color:#666;">These links expire in {ttl_hours} hours.</p>
      <p style="font-size:13px;color:#666;">Thank you for choosing LeadKar.</p>
    </div>
  </body>
</html>"""
    return subject, html, text
