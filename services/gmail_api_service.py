import os
import base64
import logging

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from app.config import settings


from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


class GmailAPIService:

    def __init__(self):
        self.service = self.authenticate()

    def authenticate(self):

        creds = None

        token_path = settings.GOOGLE_TOKEN_PATH
        cred_path = settings.GOOGLE_CREDENTIALS_PATH

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(
                token_path,
                SCOPES
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError as exc:
                    raise RuntimeError(
                        "Gmail OAuth token expired or revoked. On the server, delete "
                        "credentials/token.json and re-run OAuth setup (see README), or "
                        "update the token file with a fresh authorized token."
                    ) from exc

            else:
                if not os.path.exists(cred_path):
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {cred_path}. "
                        "Add Google OAuth client JSON from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    cred_path,
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token:
                token.write(creds.to_json())

        logger.info("GMAIL API AUTH SUCCESS")

        return build(
            "gmail",
            "v1",
            credentials=creds
        )

    def send_email(
        self,
        sender,
        recipient,
        subject,
        html_body,
        pdf_bytes=None,
        filename="report.pdf"
    ):

        try:

            message = MIMEMultipart()

            message["to"] = recipient
            message["from"] = sender
            message["subject"] = subject

            # HTML BODY
            message.attach(
                MIMEText(html_body, "html")
            )

            # PDF ATTACHMENT
            if pdf_bytes:

                part = MIMEBase(
                    "application",
                    "octet-stream"
                )

                part.set_payload(pdf_bytes)

                encoders.encode_base64(part)

                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"'
                )

                message.attach(part)

            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()

            body = {
                "raw": raw_message
            }

            response = (
                self.service.users()
                .messages()
                .send(
                    userId="me",
                    body=body
                )
                .execute()
            )

            logger.info(
                "EMAIL SENT SUCCESSFULLY TO %s",
                recipient
            )

            return response

        except Exception as e:
            logger.exception("GMAIL API SEND FAILED")
            raise e