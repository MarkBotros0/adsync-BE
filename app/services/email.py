"""Gmail SMTP email service.

Mirrors the Refs Project lib/email.ts using the same Gmail credentials
(GMAIL_USER / GMAIL_APP_PASSWORD env vars) and the same OTP flow.
"""
import logging
import random
import smtplib
import asyncio
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def generate_verification_code() -> str:
    """Generate a 6-digit OTP code (mirrors generateVerificationCode in email.ts)."""
    return str(random.randint(100000, 999999))


def _send_mail_sync(to: str, subject: str, html: str) -> bool:
    """Blocking SMTP send — called via executor so it doesn't block the event loop."""
    if not settings.gmail_user or not settings.gmail_app_password:
        logger.warning("Email send skipped: GMAIL_USER and GMAIL_APP_PASSWORD are not configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Ad Sync <{settings.gmail_user}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.gmail_user, settings.gmail_app_password)
            server.sendmail(settings.gmail_user, to, msg.as_string())
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


async def _send_mail(to: str, subject: str, html: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_send_mail_sync, to, subject, html))


async def send_verification_email(email: str, code: str, type: str = "signup") -> bool:
    """Send a 6-digit OTP for signup or password reset.

    Mirrors sendVerificationEmail() in Refs Project lib/email.ts.
    """
    subject = "Verification Code" if type == "signup" else "Password Reset Code"
    greeting = "Welcome to Ad Sync!" if type == "signup" else "Password Reset Request"
    intro = (
        "To complete your registration, please use the verification code below."
        if type == "signup"
        else "We received a request to reset your password. Use the code below to create a new password."
    )
    security_tip = (
        "Never share this code with anyone. Our team will never ask for your verification code."
        if type == "signup"
        else "If you didn't request a password reset, please ignore this email or contact support."
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background-color:#f5f5f5;font-family:Arial,sans-serif;">
      <div style="max-width:600px;margin:0 auto;padding:20px;">
        <div style="background-color:#ffffff;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.1);overflow:hidden;">

          <div style="background-color:#1a1a2e;padding:30px;text-align:center;">
            <h1 style="color:#ffffff;font-size:24px;margin:0 0 5px 0;">{greeting}</h1>
            <p style="color:#4f8ef7;font-size:14px;margin:0;">Ad Sync Platform</p>
          </div>

          <div style="padding:40px 30px;">
            <p style="font-size:16px;color:#333333;line-height:1.6;margin:0 0 30px 0;">{intro}</p>

            <div style="background-color:#f8f9fa;border:2px solid #4f8ef7;border-radius:8px;padding:25px;text-align:center;margin:30px 0;">
              <p style="color:#1a1a2e;font-size:14px;margin:0 0 15px 0;font-weight:bold;text-transform:uppercase;letter-spacing:1px;">Your Verification Code</p>
              <div style="background-color:#ffffff;border:2px dashed #4f8ef7;border-radius:6px;padding:15px;margin:0 auto;display:inline-block;">
                <p style="font-size:36px;color:#1a1a2e;letter-spacing:8px;font-weight:bold;margin:0;font-family:'Courier New',monospace;">{code}</p>
              </div>
              <p style="color:#666666;font-size:13px;margin:15px 0 0 0;">Select and copy the code above</p>
            </div>

            <div style="background-color:#fff3cd;border-left:4px solid #ffc107;padding:15px;border-radius:5px;margin:25px 0;">
              <p style="font-size:14px;color:#856404;margin:0;">
                <strong>&#9201; Important:</strong> This code will expire in 15 minutes.
              </p>
            </div>

            <div style="background-color:#e7f3ff;border-left:4px solid #2196F3;padding:15px;border-radius:5px;margin:25px 0;">
              <p style="font-size:14px;color:#0d47a1;margin:0 0 8px 0;font-weight:bold;">&#128274; Security Tip</p>
              <p style="font-size:13px;color:#1565c0;margin:0;line-height:1.5;">{security_tip}</p>
            </div>

            <p style="font-size:14px;color:#666666;line-height:1.6;margin:30px 0 0 0;text-align:center;">
              Need help? Contact our support team anytime.
            </p>
          </div>

          <div style="background-color:#f8f9fa;padding:20px;text-align:center;border-top:1px solid #e0e0e0;">
            <p style="font-size:12px;color:#999999;margin:0;">&copy; {datetime.now().year} Ad Sync Platform</p>
          </div>

        </div>
      </div>
    </body>
    </html>
    """

    return await _send_mail(email, f"Ad Sync - {subject}", html)
