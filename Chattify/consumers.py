from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import Chat, FriendRequest
from django.db.models import Q
import logging
import uuid
from django.utils.timezone import now
from django.core.files.base import ContentFile
import base64

logger = logging.getLogger(__name__)

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.debug("Starting WebSocket connection attempt")
        
        # Initialize attributes
        self.user = None
        self.sender_username = None
        self.recipient_username = None
        self.private_room_group_name = None
        self.global_room_group_name = None
        
        try:
            # Get sender username from URL
            self.sender_username = self.scope['url_route']['kwargs'].get('username')
            if not self.sender_username:
                logger.warning("No username provided in URL")
                await self.close()
                return
            
            # Authenticate the user by username
            self.user = await self.get_user_by_username(self.sender_username)
            if not self.user or not self.user.is_authenticated:
                logger.warning(f"User {self.sender_username} not authenticated")
                await self.close()
                return

            logger.debug(f"User authenticated: {self.sender_username}")
            
            # Get recipient username from URL (if present)
            self.recipient_username = self.scope['url_route']['kwargs'].get('recipient')
            
            # Set up the global room group for the user
            self.global_room_group_name = f"user_{self.sender_username}"
            
            # Set up private room group if recipient is provided
            if self.recipient_username:
                self.private_room_group_name = self.get_room_group_name(self.sender_username, self.recipient_username)
                logger.info(f"User {self.sender_username} connecting to chat with {self.recipient_username}")
            else:
                logger.info(f"User {self.sender_username} connecting to global notifications")
            
            # Accept the WebSocket connection
            await self.accept()
            
            # Add to global channel group
            await self.channel_layer.group_add(
                self.global_room_group_name,
                self.channel_name
            )
            
            # Add to private channel group if recipient is specified
            if self.recipient_username and self.private_room_group_name:
                await self.channel_layer.group_add(
                    self.private_room_group_name,
                    self.channel_name
                )
            
            # Set user status to "Online"
            cache.set(f"user_status_{self.sender_username}", "Online", timeout=None)
            
            # Broadcast user status update
            await self.channel_layer.group_send(
                self.global_room_group_name,
                {
                    'type': 'user_status',
                    'username': self.sender_username,
                    'status': 'Online',
                }
            )
            
            # Send friends status
            friends_status = await self.get_friends_online_status(self.user)
            await self.send_friends_status(friends_status)
            
        except Exception as e:
            logger.error(f"WebSocket connect error: {e}")
            await self.close()

    def get_room_group_name(self, sender_username, recipient_username):
        """Generate a unique group name for private chats, based on alphabetical order."""
        return f"{min(sender_username, recipient_username)}_{max(sender_username, recipient_username)}"
       
    @sync_to_async
    def get_user_by_username(self, username):
        """Retrieve user by username."""
        if not username:
            logger.warning("No username provided")
            return None
        
        try:
            # Fetch user from the database by username
            user = User.objects.get(username=username)
            logger.debug(f"User found: {user.username}")
            return user
        except User.DoesNotExist:
            logger.warning(f"User {username} not found")
            return None

    @sync_to_async
    def get_friends_online_status(self, user):
        """Fetch the online status of accepted friends."""
        friends = FriendRequest.objects.filter(
            Q(is_accepted=True) & (Q(from_user=user) | Q(to_user=user))
        )

        friends_statuses = {}

        for friend_request in friends:
            friend = friend_request.to_user if friend_request.from_user == user else friend_request.from_user
            status = cache.get(f"user_status_{friend.username}", "Offline")
            friends_statuses[friend.username] = status

        return friends_statuses
    
    async def user_status(self, event):
        """Handle and broadcast user status updates."""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'username': event['username'],
            'status': event['status'],
        }))

    async def send_friends_status(self, friends_statuses):
        """Send the online status of all friends to the frontend."""
        await self.send(text_data=json.dumps({
            'type': 'friends_status',
            'friends_statuses': friends_statuses
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            # If user isn't authenticated, just return
            if not hasattr(self, 'user') or self.user is None:
                logger.debug(f"Unauthenticated user disconnecting with code {close_code}")
                return

            logger.info(f"User {self.user.username} disconnecting with code {close_code}")
            
            # Remove from global room group
            if hasattr(self, 'global_room_group_name') and self.global_room_group_name:
                await self.channel_layer.group_discard(
                    self.global_room_group_name, 
                    self.channel_name
                )

                # Update user status
                cache.set(f"user_status_{self.user.username}", "Offline", timeout=None)
                
                # Broadcast status update
                await self.channel_layer.group_send(
                    self.global_room_group_name,
                    {
                        'type': 'user_status',
                        'username': self.user.username,
                        'status': 'Offline',
                    }
                )
            
            # Remove from private room group if applicable
            if hasattr(self, 'private_room_group_name') and self.private_room_group_name:
                await self.channel_layer.group_discard(
                    self.private_room_group_name, 
                    self.channel_name
                )
        except Exception as e:
            logger.error(f"Error in disconnect: {e}") 

    async def receive(self, text_data):
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            message = (data.get('message') or '').strip()
            media = data.get('media')
            typing_status = data.get('typing', False)

            # Handle typing status
            if 'typing' in data:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'show_typing',
                        'typing': typing_status,
                        'loggedInUser': self.sender_username,
                    }
                )
                return 

            # If no message and no media, send error
            if not message and not media:
                await self.send_error('You must send either a message or media')
                return

            # Handle media file
            media_file = None
            if media:
                media_file = await self.save_media_async(media)
                if not media_file:
                    await self.send_error('Invalid media file')
                    return

            # Get recipient
            recipient = await self.get_recipient_async()
            if not recipient:
                await self.send_error('Recipient does not exist')
                return

            # Save the message
            message_obj = await self.save_message_async(
                self.user, recipient, message, media_file
            )

            # Broadcast the message to the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'media': message_obj.media.url if message_obj.media else None,
                    'user': self.user.username,
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
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'message_id': event['message_id'],
            'media': event.get('media'),
            'user': event['user'],
            'recipient': event['recipient'],
            'sent_at': event['sent_at'],
            'loggedInUser': self.sender_username,
        }))

    @sync_to_async
    def save_message_async(self, user, recipient, message, media=None):
        """Save a new message to the database."""
        chat = Chat.objects.create(
            sender=user,
            recipient=recipient,
            message=message,
            media=media
        )
        return chat

    async def send_error(self, message):
        """Send error message back to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
        }))
