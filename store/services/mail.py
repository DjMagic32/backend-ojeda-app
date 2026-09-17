import logging

import resend
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


def send_app_email(subject: str, message: str, recipient: str) -> None:
    """Envía un correo transaccional.

    Usa la librería de Resend si hay RESEND_API_KEY (Railway bloquea los
    puertos SMTP salientes, así que SMTP se cuelga allí). Si no, cae al
    backend de email de Django (SMTP con timeout o consola en dev).
    """
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if api_key:
        resend.api_key = api_key
        try:
            result = resend.Emails.send(
                {
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [recipient],
                    "subject": subject,
                    "text": message,
                }
            )
        except Exception as exc:
            logger.error("Resend rechazó el envío a %s: %s", recipient, exc)
            raise EmailDeliveryError("No se pudo enviar el correo") from exc
        logger.info("Email enviado vía Resend, id=%s", result.get("id"))
        return

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[recipient],
        fail_silently=False,
    )
