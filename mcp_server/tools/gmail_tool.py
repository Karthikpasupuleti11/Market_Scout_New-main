from services.gmail_api_service import GmailAPIService
from app.config import settings

gmail_service = GmailAPIService()


def send_market_report(
    recipient,
    company,
    html_body,
    pdf_bytes=None
):

    subject = f"📊 Market Intelligence Report — {company}"

    return gmail_service.send_email(
        sender=settings.EMAIL_SENDER,
        recipient=recipient,
        subject=subject,
        html_body=html_body,
        pdf_bytes=pdf_bytes,
        filename=f"{company}.pdf"
    )