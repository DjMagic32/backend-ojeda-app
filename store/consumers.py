import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async # For database operations
from .models import ChatRoom, ChatMessage, Usuario

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Validate if room_name is a valid ChatRoom ID and user is a participant
        # For simplicity, we'll assume room_name is the ID of the ChatRoom for now.
        # A more robust approach might involve a UUID for room names or more complex lookup.
        try:
            self.chat_room_id = int(self.room_name)
            self.chat_room = await self.get_chat_room(self.chat_room_id)
            if self.chat_room is None or not await self.is_user_participant(self.chat_room, self.user):
                await self.close()
                return
        except ValueError:
            # Room name is not an integer ID
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"User {self.user.username} connected to room {self.room_group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'): # Ensure room_group_name was set
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"User {self.user.username if self.user.is_authenticated else 'Anonymous'} disconnected from room {self.room_group_name}")

    # Receive message from WebSocket
    async def receive(self, text_data):
        if not self.user.is_authenticated:
            return # Should not happen if connect() closed for unauthenticated

        text_data_json = json.loads(text_data)
        message_content = text_data_json.get('message')
        message_type = text_data_json.get('message_type', ChatMessage.MESSAGE_TYPE_TEXT) # Default to text

        if not message_content and message_type == ChatMessage.MESSAGE_TYPE_TEXT:
            print("Received empty text message, ignoring.")
            return

        # Save message to database
        chat_message = await self.save_message(self.chat_room, self.user, message_content, message_type)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message_event', # This will call chat_message_event method
                'message_id': chat_message.id,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'content': chat_message.content,
                'timestamp': chat_message.timestamp.isoformat(),
                'message_type': chat_message.message_type,
            }
        )
        print(f"User {self.user.username} sent message to room {self.room_group_name}")


    # Receive message from room group and send to WebSocket
    async def chat_message_event(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'message_type': event['message_type'],
        }))
        print(f"Sent message event to WebSocket in room {self.room_group_name}")

    @database_sync_to_async
    def get_chat_room(self, room_id):
        try:
            return ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def is_user_participant(self, room, user):
        if not room or not user.is_authenticated:
            return False
        return room.participants.filter(id=user.id).exists()

    @database_sync_to_async
    def save_message(self, room, sender, content, message_type):
        return ChatMessage.objects.create(
            room=room,
            sender=sender,
            content=content,
            message_type=message_type
        )
