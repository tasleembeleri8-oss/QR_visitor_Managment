import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor


def generate_visitor_pass_pdf(visit, qr_absolute_path) -> io.BytesIO:
    """
    Builds a printable visitor pass PDF with the QR code and visit details.
    Returns an in-memory BytesIO buffer ready to send as a file.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    ink = HexColor("#14171C")
    green = HexColor("#00A876")
    dim = HexColor("#5C6577")

    # Card background
    card_w, card_h = 110 * mm, 160 * mm
    card_x = (width - card_w) / 2
    card_y = height - card_h - 40 * mm

    c.setFillColor(ink)
    c.roundRect(card_x, card_y, card_w, card_h, 6 * mm, fill=1, stroke=0)

    # Header
    c.setFillColor(green)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, card_y + card_h - 20 * mm, "GATEPASS")

    c.setFillColor(dim)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, card_y + card_h - 27 * mm, "VISITOR PASS")

    # QR code
    qr_size = 55 * mm
    qr_x = width / 2 - qr_size / 2
    qr_y = card_y + card_h - 95 * mm
    c.drawImage(qr_absolute_path, qr_x, qr_y, width=qr_size, height=qr_size)

    # Visitor details
    text_y = qr_y - 12 * mm
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, text_y, visit.visitor.name)

    c.setFillColor(dim)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, text_y - 7 * mm, f"Visiting: {visit.host.name}")
    if visit.host.department:
        c.drawCentredString(width / 2, text_y - 13 * mm, visit.host.department)
    if visit.purpose:
        c.drawCentredString(width / 2, text_y - 19 * mm, visit.purpose)

    c.setFont("Helvetica", 7)
    c.drawCentredString(width / 2, card_y + 10 * mm, f"TOKEN: {visit.token}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer