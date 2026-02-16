from django.core.mail import send_mail
import os
from core.constants import ADMIN_EMAIL, LIBRARY_EMAIL


def admin_alert(subject: str, message: str):
    send_mail(subject, message, from_email=os.getenv(
        'NOREPLY_EMAIL'), recipient_list=[ADMIN_EMAIL])


def librarian_alert(subject: str, message: str):
    send_mail(subject, message, from_email=os.getenv(
        'NOREPLY_EMAIL'), recipient_list=[LIBRARY_EMAIL])


def student_alert(subject: str, message: str, recipient: str):
    send_mail(subject, message, from_email=os.getenv(
        'NOREPLY_EMAIL'), recipient_list=[recipient])
