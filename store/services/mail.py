import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailDeliveryError(Exception):
    pass


def send_app_email(subject: str, message: str, recipient: str) -> None:
    """Envía un correo transaccional.

    Usa la API HTTP de Resend si hay RESEND_API_KEY (Railway bloquea los
    puertos SMTP salientes, así que SMTP se cuelga allí). Si no, cae al
    backend de email de Django (SMTP con timeout o consola en dev).
    """
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if api_key:
        try:
            response = requests.post(
                RESEND_API_URL,
                json={
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [recipient],
                    "subject": subject,
                    "text": message,
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.error("Error de red enviando email vía Resend: %s", exc)
            raise EmailDeliveryError("No se pudo enviar el correo") from exc
        if response.status_code >= 400:
            logger.error(
                "Resend respondió %s: %s", response.status_code, response.text
            )
            raise EmailDeliveryError("No se pudo enviar el correo")
        return

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[recipient],
        fail_silently=False,
    )
