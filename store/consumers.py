"""Consumers WebSocket para chat y notificaciones en tiempo real."""

from __future__ import annotations

import json
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Stream bidireccional para mensajes de una conversación.

    URL: ``/ws/chat/<conversation_id>/?token=<jwt>``

    Mensajes que el cliente envía:
    - ``{"type": "message.send", "contenido": "..."}``
    - ``{"type": "typing", "typing": true}``
    - ``{"type": "read"}``

    Eventos que el servidor envía:
    - ``{"type": "chat.message", "payload": MessageSerializer}``
    - ``{"type": "chat.typing", "user_id": id, "typing": bool}``
    - ``{"type": "chat.read", "payload": {...}}``
    """

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.conversation_id = int(self.scope['url_route']['kwargs']['conversation_id'])
        if not await self._user_is_participant(self.conversation_id, user.id):
            await self.close(code=4403)
            return

        self.group_name = f'chat_{self.conversation_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):  # noqa: D401
        group = getattr(self, 'group_name', None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content: dict[str, Any], **kwargs):
        msg_type = content.get('type')
        user = self.scope['user']

        if msg_type == 'message.send':
            contenido = (content.get('contenido') or '').strip()
            if not contenido:
                return
            payload = await self._save_message(self.conversation_id, user.id, contenido)
            # send_message en views ya hace el broadcast vía REST. Aquí
            # cubrimos el camino WS-only para clientes que prefieran enviar
            # mensajes por socket sin pasar por REST.
            from .services.realtime import broadcast_chat_message

            broadcast_chat_message(self.conversation_id, payload)
            await self._notify_recipients(self.conversation_id, user.id, contenido)

        elif msg_type == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.typing',
                    'user_id': user.id,
                    'typing': bool(content.get('typing', True)),
                },
            )

        elif msg_type == 'read':
            await self._mark_read(self.conversation_id, user.id)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.read',
                    'payload': {'conversation_id': self.conversation_id, 'reader_id': user.id},
                },
            )

    # Handlers para eventos del grupo ---------------------------------------------------

    async def chat_message(self, event):
        await self.send_json({'type': 'message', 'payload': event['payload']})

    async def chat_typing(self, event):
        # No reenviar a uno mismo
        if event.get('user_id') == self.scope['user'].id:
            return
        await self.send_json({'type': 'typing', 'user_id': event['user_id'], 'typing': event['typing']})

    async def chat_read(self, event):
        await self.send_json({'type': 'read', 'payload': event['payload']})

    # DB helpers ------------------------------------------------------------------------

    @database_sync_to_async
    def _user_is_participant(self, conversation_id: int, user_id: int) -> bool:
        from .models import Conversation

        return Conversation.objects.filter(id=conversation_id, participantes__id=user_id).exists()

    @database_sync_to_async
    def _save_message(self, conversation_id: int, autor_id: int, contenido: str) -> dict[str, Any]:
        from .models import Conversation, Message
        from .serializers import MessageSerializer

        conversacion = Conversation.objects.get(id=conversation_id)
        mensaje = Message.objects.create(
            conversation=conversacion,
            autor_id=autor_id,
            contenido=contenido,
        )
        conversacion.save(update_fields=['actualizado'])
        return MessageSerializer(mensaje).data

    @database_sync_to_async
    def _mark_read(self, conversation_id: int, user_id: int) -> int:
        from .models import Message

        return (
            Message.objects.filter(conversation_id=conversation_id, leido=False)
            .exclude(autor_id=user_id)
            .update(leido=True)
        )

    @database_sync_to_async
    def _notify_recipients(self, conversation_id: int, autor_id: int, contenido: str):
        from .models import Conversation, Notificacion, Usuario
        from .services.push import send_push_to_user

        try:
            conversacion = Conversation.objects.prefetch_related('participantes').get(id=conversation_id)
        except Conversation.DoesNotExist:
            return
        autor = Usuario.objects.filter(id=autor_id).first()
        if autor is None:
            return
        autor_nombre = autor.first_name or autor.email
        for destinatario in conversacion.participantes.exclude(id=autor_id):
            Notificacion.objects.create(
                usuario=destinatario,
                titulo=f'Nuevo mensaje de {autor_nombre}',
                mensaje=contenido[:140],
                tipo=Notificacion.TIPO_MENSAJE,
                data={'conversation_id': conversation_id},
                leido=False,
            )
            send_push_to_user(
                destinatario.id,
                title=f'Nuevo mensaje de {autor_nombre}',
                body=contenido[:140],
                data={'type': 'chat', 'conversation_id': conversation_id},
            )


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Stream personal de notificaciones para el usuario autenticado.

    URL: ``/ws/notifications/?token=<jwt>``
    """

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group_name = f'user_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):  # noqa: D401
        group = getattr(self, 'group_name', None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def notification_message(self, event):
        await self.send_json({'type': 'notification', 'payload': event['payload']})
