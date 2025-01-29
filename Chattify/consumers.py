from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
import json
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.core.cache import cache
from .models import Chat
from django.core.files.base import ContentFile
import base64
import uuid
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.debug(f"Connecting user: {self.scope['user']}")
        self.user = await self.get_user()

        if not self.user.is_authenticated:
            logger.warning("User not authenticated")
            await self.close()
            return

        self.message_count = 0
        self.sender = self.user
        self.recipient_username = self.scope['url_route']['kwargs']['username']
        self.room_group_name = self.get_room_group_name(self.sender.username, self.recipient_username)

        logger.info(f"User {self.sender.username} connecting to room {self.room_group_name}")

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        cache.set(f"user_status_{self.user.username}", "Online", timeout=None)
        await self.accept()

    @database_sync_to_async
    def get_user(self):
        token_key = self.scope['query_string'].decode().split('=')[-1]
        try:
            user = Token.objects.get(key=token_key).user
            return user
        except Token.DoesNotExist:
            return AnonymousUser()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        cache.set(f"user_status_{self.user.username}", "Offline", timeout=None)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = (data.get('message') or '').strip()
            media = data.get('media')
            typing_status = data.get('typing', False)

            if 'typing' in data:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'show_typing',
                        'typing': typing_status,
                        'loggedInUser': self.sender.username,
                    }
                )
                return 

            if not message and not media:
                await self.send_error('You must send either a message or media')
                return

            media_file = None
            if media:
                media_file = await self.save_media_async(media)
                if not media_file:
                    await self.send_error('Invalid media file')
                    return

            recipient = await self.get_recipient_async()
            if not recipient:
                await self.send_error('Recipient does not exist')
                return

            message_obj = await self.save_message_async(
                self.sender, recipient, message, media_file
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'media': message_obj.media.url if message_obj.media else None,
                    'user': self.sender.username,
                    'recipient': recipient.username,
                    'message_id': message_obj.id,
                    'sent_at': message_obj.sent_at.isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send_error("An unexpected error occurred.")

    async def show_typing(self, event):
        """Handle and broadcast typing status."""
        username = event['loggedInUser']
        typing = event['typing']

        await self.send(text_data=json.dumps({
            'type': 'typing',
            'loggedInUser': username,
            'typing': typing,
        }))

    async def chat_message(self, event):
        """Handle and broadcast chat messages."""
        self.message_count += 1

        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'message_id': event['message_id'],
            'media': event.get('media'),
            'user': event['user'],
            'recipient': event['recipient'],
            'sent_at': event['sent_at'],
            'loggedInUser': self.sender.username,
            'incomingMessageCount': self.message_count,
        }))

    @sync_to_async
    def save_message_async(self, user, recipient, message, media=None):
        return Chat.objects.create(
            user=user,
            recipient=recipient,
            message=message,
            media=media,
            sent_at=now(),
        )

    @sync_to_async
    def save_media_async(self, media):
        try:
            format, imgstr = media.split(';base64,')
            ext = format.split('/')[-1]
            filename = f"{now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{ext}"
            file_data = ContentFile(base64.b64decode(imgstr), name=filename)
            return file_data
        except Exception as e:
            logger.error(f"Error saving media: {e}")
            return None

    async def send_error(self, error_message):
        await self.send(text_data=json.dumps({'error': error_message}))

    def get_room_group_name(self, sender_username, recipient_username):
        return f"{min(sender_username, recipient_username)}_{max(sender_username, recipient_username)}"

    @sync_to_async
    def get_recipient_async(self):
        try:
            return User.objects.get(username=self.recipient_username)
        except User.DoesNotExist:
            return None
