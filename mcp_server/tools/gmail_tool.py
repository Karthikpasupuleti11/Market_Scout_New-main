from app.config import settings

_gmail_service = None


def _get_gmail_service():
    """Create Gmail client on first send — not at import (avoids OAuth on /schedules)."""
    global _gmail_service
    if _gmail_service is None:
        from services.gmail_api_service import GmailAPIService

        _gmail_service = GmailAPIService()
    return _gmail_service


def send_market_report(
    recipient,
    company,
    html_body,
    pdf_bytes=None,
):
    subject = f"📊 Market Intelligence Report — {company}"

    return _get_gmail_service().send_email(
        sender=settings.EMAIL_SENDER,
        recipient=recipient,
        subject=subject,
        html_body=html_body,
        pdf_bytes=pdf_bytes,
        filename=f"{company}.pdf",
    )
