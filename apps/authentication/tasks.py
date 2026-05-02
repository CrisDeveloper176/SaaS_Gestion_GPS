from celery import shared_task
from shared.utils.email_service import get_email_service

@shared_task
def send_invite_email_task(email, subject, message):
    email_service = get_email_service()
    email_service.send(
        subject=subject,
        message=message,
        recipient_list=[email]
    )
    return {'status': 'sent', 'email': email}
