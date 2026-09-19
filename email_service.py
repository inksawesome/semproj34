import os
import secrets
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from dotenv import load_dotenv


load_dotenv()


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)

APP_BASE_URL = os.getenv(
    "APP_BASE_URL",
    "http://localhost:8501"
)


# Temporary in-memory storage.
# PostgreSQL will replace this later.
verification_requests = {}


def create_verification_request(email):
    """
    Create a unique verification token for a signup request.
    """

    token = secrets.token_urlsafe(32)

    verification_requests[token] = {
        "email": email,
        "status": "pending"
    }

    return token


def send_verification_email(email):
    """
    Send the Yes/No authentication email.
    """

    token = create_verification_request(email)

    yes_url = (
        f"{APP_BASE_URL}"
        f"?email_action=yes"
        f"&token={quote(token)}"
    )

    no_url = (
        f"{APP_BASE_URL}"
        f"?email_action=no"
        f"&token={quote(token)}"
    )

    message = EmailMessage()

    message["Subject"] = "Biometric Authentication - Verify Signup"
    message["From"] = EMAIL_FROM
    message["To"] = email

    message.set_content(
        f"""
Biometric Authentication

Someone has requested to register a biometric account
using this email address.

Was this you?

YES, IT'S ME:
{yes_url}

NO, IT'S NOT ME:
{no_url}

If you did not initiate this request, choose
"No, It's Not Me".

        """
    )

    try:

        with smtplib.SMTP_SSL(
            SMTP_HOST,
            SMTP_PORT
        ) as server:

            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD
            )

            server.send_message(message)

        return True, token

    except Exception as e:

        # Remove failed request
        verification_requests.pop(token, None)

        return False, str(e)


def process_email_response(token, action):
    """
    Process the Yes/No response from the email.
    """

    request = verification_requests.get(token)

    if request is None:
        return "invalid"

    if action == "yes":

        request["status"] = "approved"
        return "approved"

    if action == "no":

        request["status"] = "denied"
        return "denied"

    return "invalid"


def get_request_status(token):
    """
    Get current status of a verification request.
    """

    request = verification_requests.get(token)

    if request is None:
        return None

    return request["status"]