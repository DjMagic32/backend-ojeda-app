"""Cliente delgado para la API de Expo Push Notifications.

Funciona sin SDK adicional: solo necesita ``requests``. Si el envío falla
de forma persistente (ej. token "DeviceNotRegistered"), elimina el token
de la base de datos para no seguir reintentando.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

import requests

from django.conf import settings

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'
EXPO_BATCH_SIZE = 100


def _build_messages(tokens: Iterable[str], title: str, body: str, data: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = []
    for token in tokens:
        if not token:
            continue
        message: dict[str, Any] = {
            'to': token,
            'title': title,
            'body': body,
            'sound': 'default',
            'priority': 'high',
        }
        if data is not None:
            message['data'] = data
        payload.append(message)
    return payload


def send_push(tokens: Iterable[str], title: str, body: str, data: dict[str, Any] | None = None) -> None:
    """Envía una push notification a uno o varios tokens de Expo.

    Limpia tokens inválidos del modelo ``ExpoPushToken`` cuando Expo responde
    con ``DeviceNotRegistered`` o ``InvalidCredentials``.
    """

    from store.models import ExpoPushToken  # local import para evitar ciclos

    messages = _build_messages(tokens, title, body, data)
    if not messages:
        return

    for i in range(0, len(messages), EXPO_BATCH_SIZE):
        batch = messages[i : i + EXPO_BATCH_SIZE]
        try:
            response = requests.post(EXPO_PUSH_URL, json=batch, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            logger.exception('Fallo enviando push a Expo')
            continue

        try:
            data_response = response.json().get('data', [])
        except ValueError:
            logger.warning('Respuesta inesperada de Expo: %s', response.text[:200])
            continue

        for ticket, message in zip(data_response, batch):
            if ticket.get('status') != 'error':
                continue
            error_code = (ticket.get('details') or {}).get('error')
            if error_code in {'DeviceNotRegistered', 'InvalidCredentials'}:
                ExpoPushToken.objects.filter(token=message['to']).delete()
                logger.info('Token Expo inválido eliminado: %s', message['to'])


def send_push_to_user(user_id: int, title: str, body: str, data: dict[str, Any] | None = None) -> None:
    from store.models import ExpoPushToken

    if getattr(settings, 'EXPO_PUSH_DISABLED', False):
        return

    tokens = list(
        ExpoPushToken.objects.filter(usuario_id=user_id).values_list('token', flat=True)
    )
    if tokens:
        send_push(tokens, title, body, data)
