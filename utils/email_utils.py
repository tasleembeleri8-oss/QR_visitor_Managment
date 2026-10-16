from flask_mail import Message
from extensions import mail


def send_visitor_qr_email(visitor_email, visitor_name, host_name, qr_absolute_path):
    """Emails the visitor their QR code pass after registration."""
    msg = Message(
        subject="Your Visitor Pass QR Code",
        recipients=[visitor_email],
    )
    msg.body = (
        f"Hi {visitor_name},\n\n"
        f"Your visit has been registered. You're meeting {host_name}.\n"
        f"Please show the attached QR code at the entrance for check-in.\n\n"
        f"See you soon!"
    )
    with open(qr_absolute_path, "rb") as f:
        msg.attach("visitor_pass.png", "image/png", f.read())

    mail.send(msg)


def send_host_arrival_email(host_email, host_name, visitor_name, purpose):
    """Notifies the host that their visitor has checked in."""
    msg = Message(
        subject=f"{visitor_name} has arrived",
        recipients=[host_email],
    )
    msg.body = (
        f"Hi {host_name},\n\n"
        f"Your visitor {visitor_name} has just checked in at the front desk.\n"
        f"Purpose of visit: {purpose or 'Not specified'}\n\n"
        f"Please come collect them at reception."
    )
    mail.send(msg)
