"""Helpers para emitir eventos WebSocket vía Django Channels.

Encapsula la importación de ``channels.layers`` y el uso de ``async_to_sync``
para poder llamarse desde código síncrono (signals, viewsets) sin acoplarlos
a la API asíncrona de Channels.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _channel_layer():
    try:
        from channels.layers import get_channel_layer

        return get_channel_layer()
    except Exception:  # noqa: BLE001 — si Channels no está instalado, ignorar
        return None


def _send(group: str, payload: dict[str, Any]) -> None:
    layer = _channel_layer()
    if layer is None:
        return
    from asgiref.sync import async_to_sync

    try:
        async_to_sync(layer.group_send)(group, payload)
    except Exception:  # noqa: BLE001 — no romper la request por un fallo de pub/sub
        logger.exception('Fallo enviando evento WebSocket al grupo %s', group)


def notify_user(user_id: int, payload: dict[str, Any]) -> None:
    """Envía una notificación al canal personal del usuario."""
    _send(f'user_{user_id}', {'type': 'notification.message', 'payload': payload})


def broadcast_chat_message(conversation_id: int, payload: dict[str, Any]) -> None:
    """Envía un mensaje nuevo al grupo de la conversación."""
    _send(f'chat_{conversation_id}', {'type': 'chat.message', 'payload': payload})


def broadcast_chat_read(conversation_id: int, reader_id: int) -> None:
    _send(
        f'chat_{conversation_id}',
        {'type': 'chat.read', 'payload': {'conversation_id': conversation_id, 'reader_id': reader_id}},
    )
