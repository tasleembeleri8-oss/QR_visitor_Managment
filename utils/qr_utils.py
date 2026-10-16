import os
import qrcode


def generate_qr(token: str, folder: str) -> str:
    """
    Generates a QR code image encoding just the visit's token (not personal
    data). Returns the relative path (under /static) to store on the Visit row.
    """
    os.makedirs(folder, exist_ok=True)
    filename = f"{token}.png"
    filepath = os.path.join(folder, filename)

    img = qrcode.make(token)
    img.save(filepath)

    return f"qrcodes/{filename}"
