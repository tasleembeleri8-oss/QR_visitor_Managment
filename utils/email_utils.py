
import base64
import os

import resend
from flask import current_app


def _send_email(to_email, subject, text_body, attachment_path=None):
    """Send an email using Resend's HTTPS API."""
    api_key = os.environ.get("RESEND_API_KEY")

    if not api_key:
        current_app.logger.error("RESEND_API_KEY is not configured.")
        return False

    sender = os.environ.get(
        "RESEND_FROM_EMAIL",
        "onboarding@resend.dev",
    )

    params = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
    }

    if attachment_path:
        with open(attachment_path, "rb") as image_file:
            encoded_image = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        params["attachments"] = [
            {
                "filename": "visitor_pass.png",
                "content": encoded_image,
            }
        ]

    try:
        resend.api_key = api_key
        result = resend.Emails.send(params)
        current_app.logger.info("Email accepted by Resend.")
        return True
    except Exception:
        current_app.logger.exception("Resend email delivery request failed.")
        return False


def send_visitor_qr_email(
    visitor_email, visitor_name, host_name, qr_absolute_path
):
    """Email the visitor their QR code pass."""
    return _send_email(
        to_email=visitor_email,
        subject="Your Visitor Pass QR Code",
        text_body=(
            f"Hi {visitor_name},\n\n"
            f"Your visit has been registered. You're meeting {host_name}.\n"
            "Please show the attached QR code at the entrance "
            "for check-in.\n\n"
            "See you soon!"
        ),
        attachment_path=qr_absolute_path,
    )


def send_host_arrival_email(host_email, host_name, visitor_name, purpose):
    """Email the host when their visitor arrives."""
    return _send_email(
        to_email=host_email,
        subject=f"{visitor_name} has arrived",
        text_body=(
            f"Hi {host_name},\n\n"
            f"Your visitor {visitor_name} has just checked in "
            "at the front desk.\n"
            f"Purpose of visit: {purpose or 'Not specified'}\n\n"
            "Please come collect them at reception."
        ),
    )
