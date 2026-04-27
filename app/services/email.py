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
    msg["From"] = f"Echofold <{settings.gmail_user}>"
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


def _send_mail_with_attachment_sync(
    to: str,
    subject: str,
    body: str,
    attachment: bytes,
    attachment_filename: str,
    attachment_mime: str,
) -> bool:
    """Blocking SMTP send with one binary attachment (used by the report runner)."""
    if not settings.gmail_user or not settings.gmail_app_password:
        logger.warning("Email-with-attachment skipped: Gmail credentials not configured")
        return False

    from email.mime.application import MIMEApplication

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = f"Echofold <{settings.gmail_user}>"
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))

    main, _, sub = (attachment_mime or "application/octet-stream").partition("/")
    part = MIMEApplication(attachment, _subtype=sub or "octet-stream")
    part.add_header("Content-Disposition", "attachment", filename=attachment_filename)
    msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.gmail_user, settings.gmail_app_password)
            server.sendmail(settings.gmail_user, to, msg.as_string())
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to send email to %s: %s", to, e)
        return False


async def send_email_with_attachment(
    *,
    to: str,
    subject: str,
    body: str,
    attachment: bytes,
    attachment_filename: str,
    attachment_mime: str,
) -> bool:
    """Async wrapper used by the scheduled-report runner."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(
            _send_mail_with_attachment_sync,
            to, subject, body, attachment, attachment_filename, attachment_mime,
        ),
    )


async def send_verification_email(email: str, code: str, type: str = "signup") -> bool:
    """Send a 6-digit OTP for signup or password reset.

    Mirrors sendVerificationEmail() in Refs Project lib/email.ts.
    """
    subject = "Verification Code" if type == "signup" else "Password Reset Code"
    greeting = "Welcome to Echofold!" if type == "signup" else "Password Reset Request"
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
    <body style="margin:0;padding:0;background-color:#0e0e13;font-family:Arial,sans-serif;">
      <div style="max-width:600px;margin:0 auto;padding:20px;background-color:#0e0e13;">
        <div style="background-color:#15151d;border-radius:12px;border:1px solid #28283a;overflow:hidden;">

          <div style="background:linear-gradient(135deg,#1d1d28 0%,#15151d 100%);padding:32px 30px;text-align:center;border-bottom:1px solid #28283a;">
            <div style="display:inline-block;background-color:#2d1b4e;border-radius:10px;padding:8px 16px;margin-bottom:16px;">
              <span style="color:#06b6d4;font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;">&#9679; Listening</span>&nbsp;&nbsp;<span style="color:#e9d5ff;font-size:14px;font-weight:700;letter-spacing:0.3px;">Echofold</span>
            </div>
            <h1 style="color:#f1e8ff;font-size:22px;font-weight:700;margin:0 0 6px 0;">{greeting}</h1>
            <p style="color:#9f7bc0;font-size:13px;margin:0;">Brand Intelligence Platform</p>
          </div>

          <div style="padding:36px 30px;background-color:#15151d;">
            <p style="font-size:15px;color:#c4b5d9;line-height:1.7;margin:0 0 28px 0;">{intro}</p>

            <div style="background-color:#1d1d28;border:1px solid #3d2e5e;border-radius:10px;padding:28px;text-align:center;margin:28px 0;">
              <p style="color:#9f7bc0;font-size:12px;margin:0 0 14px 0;font-weight:600;text-transform:uppercase;letter-spacing:1.5px;">Your Verification Code</p>
              <div style="background-color:#0e0e13;border:2px dashed #7c3aed;border-radius:8px;padding:18px 24px;display:inline-block;margin-bottom:14px;">
                <p style="font-size:38px;color:#e9d5ff;letter-spacing:10px;font-weight:700;margin:0;font-family:'Courier New',monospace;">{code}</p>
              </div>
              <p style="color:#6b5480;font-size:12px;margin:0;">Select and copy the code above</p>
            </div>

            <div style="background-color:#1d1d28;border-left:3px solid #a855f7;border-radius:6px;padding:14px 16px;margin:22px 0;">
              <p style="font-size:13px;color:#c084fc;margin:0;">
                <strong>&#9201; Important:</strong> <span style="color:#9f7bc0;">This code will expire in 15 minutes.</span>
              </p>
            </div>

            <div style="background-color:#1d1d28;border-left:3px solid #6d28d9;border-radius:6px;padding:14px 16px;margin:22px 0;">
              <p style="font-size:13px;color:#c084fc;margin:0 0 6px 0;font-weight:600;">&#128274; Security Tip</p>
              <p style="font-size:13px;color:#9f7bc0;margin:0;line-height:1.6;">{security_tip}</p>
            </div>

            <p style="font-size:13px;color:#6b5480;line-height:1.6;margin:28px 0 0 0;text-align:center;">
              Need help? Contact our support team anytime.
            </p>
          </div>

          <div style="background-color:#0e0e13;padding:18px;text-align:center;border-top:1px solid #28283a;">
            <p style="font-size:12px;color:#4a3a5e;margin:0;">&copy; {datetime.now().year} Echofold. All rights reserved.</p>
          </div>

        </div>
      </div>
    </body>
    </html>
    """

    return await _send_mail(email, f"Echofold · {subject}", html)


async def send_invitation_email(
    email: str,
    invite_url: str,
    org_name: str,
    inviter_name: str,
    role: str = "NORMAL",
) -> bool:
    """Send an invitation link to a new user.

    - role=NORMAL    → invited to a specific brand workspace
    - role=ORG_ADMIN → invited as an admin of the whole organization

    The link is valid for 24 hours and expires after first use.
    """
    is_admin_invite = role == "ORG_ADMIN"

    if is_admin_invite:
        context_line = (
            f'<strong style="color:#e9d5ff;">{inviter_name}</strong> has invited you to become an '
            f'<strong style="color:#e9d5ff;">Admin</strong> of '
            f'<strong style="color:#e9d5ff;">{org_name}</strong> on Echofold.'
        )
        role_badge = (
            '<div style="display:inline-block;background-color:#3b1f6e;border:1px solid #7c3aed;'
            'border-radius:6px;padding:4px 12px;margin-bottom:20px;">'
            '<span style="color:#c084fc;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">Org Admin</span>'
            '</div>'
        )
        cta_note = 'As an admin, you will have access to all brands within this organization.'
    else:
        context_line = (
            f'<strong style="color:#e9d5ff;">{inviter_name}</strong> has invited you to join '
            f'<strong style="color:#e9d5ff;">{org_name}</strong> on Echofold.'
        )
        role_badge = ''
        cta_note = 'Click the button below to set your password and access your account.'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background-color:#0e0e13;font-family:Arial,sans-serif;">
      <div style="max-width:600px;margin:0 auto;padding:20px;">
        <div style="background-color:#15151d;border-radius:12px;border:1px solid #28283a;overflow:hidden;">

          <div style="background:linear-gradient(135deg,#1d1d28 0%,#15151d 100%);padding:32px 30px;text-align:center;border-bottom:1px solid #28283a;">
            <div style="display:inline-block;background-color:#2d1b4e;border-radius:10px;padding:8px 16px;margin-bottom:16px;">
              <span style="color:#06b6d4;font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;">&#9679; Listening</span>&nbsp;&nbsp;<span style="color:#e9d5ff;font-size:14px;font-weight:700;letter-spacing:0.3px;">Echofold</span>
            </div>
            <h1 style="color:#f1e8ff;font-size:22px;font-weight:700;margin:0 0 6px 0;">You've been invited!</h1>
            <p style="color:#9f7bc0;font-size:13px;margin:0;">Brand Intelligence Platform</p>
          </div>

          <div style="padding:36px 30px;background-color:#15151d;">
            {role_badge}
            <p style="font-size:15px;color:#c4b5d9;line-height:1.7;margin:0 0 16px 0;">
              {context_line}
            </p>
            <p style="font-size:14px;color:#9f7bc0;line-height:1.7;margin:0 0 32px 0;">
              {cta_note}
            </p>

            <div style="text-align:center;margin:32px 0;">
              <a href="{invite_url}"
                 style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#a855f7);color:#ffffff;font-size:15px;font-weight:700;
                        padding:14px 40px;border-radius:8px;text-decoration:none;letter-spacing:0.4px;box-shadow:0 4px 20px rgba(168,85,247,0.3);">
                Accept Invitation &rarr;
              </a>
            </div>

            <div style="background-color:#1d1d28;border-left:3px solid #a855f7;border-radius:6px;padding:14px 16px;margin:22px 0;">
              <p style="font-size:13px;color:#c084fc;margin:0;">
                <strong>&#9201; Important:</strong> <span style="color:#9f7bc0;">This link expires in 24 hours and can only be used once.</span>
              </p>
            </div>

            <div style="background-color:#1d1d28;border-left:3px solid #6d28d9;border-radius:6px;padding:14px 16px;margin:22px 0;">
              <p style="font-size:13px;color:#c084fc;margin:0 0 6px 0;font-weight:600;">&#128274; Security Note</p>
              <p style="font-size:13px;color:#9f7bc0;margin:0;line-height:1.6;">
                If you did not expect this invitation, you can safely ignore this email.
              </p>
            </div>

            <p style="font-size:12px;color:#4a3a5e;margin:24px 0 0 0;line-height:1.6;">
              Or copy this link into your browser:<br>
              <span style="color:#a855f7;word-break:break-all;">{invite_url}</span>
            </p>
          </div>

          <div style="background-color:#0e0e13;padding:18px;text-align:center;border-top:1px solid #28283a;">
            <p style="font-size:12px;color:#4a3a5e;margin:0;">&copy; {datetime.now().year} Echofold. All rights reserved.</p>
          </div>

        </div>
      </div>
    </body>
    </html>
    """

    return await _send_mail(email, "Echofold · You've been invited", html)
