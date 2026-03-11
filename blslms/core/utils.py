import logging
from django.core.mail import send_mail
import os
from core.constants import ADMIN_EMAIL, LIBRARY_EMAIL

logger = logging.getLogger('blslms')


def _safe_send(subject: str, message: str, recipient_list: list[str]):
    """Send email, logging failures instead of crashing the caller."""
    try:
        send_mail(
            subject, message,
            from_email=os.getenv('NOREPLY_EMAIL'),
            recipient_list=recipient_list,
        )
    except Exception as exc:
        logger.error(
            'EMAIL_SEND_FAIL | to=%s | subject=%s | error=%s',
            recipient_list, subject, exc,
        )


def admin_alert(subject: str, message: str):
    _safe_send(subject, message, [ADMIN_EMAIL])


def librarian_alert(subject: str, message: str):
    _safe_send(subject, message, [LIBRARY_EMAIL])


def student_alert(subject: str, message: str, recipient: str):
    _safe_send(subject, message, [recipient])
