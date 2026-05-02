from django.core.mail import send_mail
from django.conf import settings
from typing import List

class EmailService:
    """Interfaz base para envío de correos."""
    def send(self, subject: str, message: str, recipient_list: List[str]):
        raise NotImplementedError

class ConsoleEmailProvider(EmailService):
    """Implementación Dummy que usa el backend de consola de Django."""
    def send(self, subject: str, message: str, recipient_list: List[str]):
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fleet.com'),
            recipient_list=recipient_list,
            fail_silently=False,
        )

# Factory o Singleton
def get_email_service() -> EmailService:
    # A futuro, aquí se decidirá si retornar ConsoleEmailProvider o ResendEmailProvider
    return ConsoleEmailProvider()
