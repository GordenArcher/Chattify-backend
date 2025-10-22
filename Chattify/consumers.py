from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.core.cache import cache
from .models import Chat, FriendRequest
from django.core.files.base import ContentFile
import base64
from django.db.models import Q
import uuid
from django.contrib.auth.models import AnonymousUser
import logging
from rest_framework_simplejwt.tokens import AccessToken
import urllib.parse


logger = logging.getLogger(__name__)

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("=" * 50)
        logger.info("NEW WEBSOCKET CONNECTION ATTEMPT")
        logger.info("=" * 50)
        
        # Get authenticated user from cookies
        self.user = await self.get_user()
        
        logger.info(f"User object: {self.user}")
        logger.info(f"User type: {type(self.user)}")
        logger.info(f"Is authenticated: {self.user.is_authenticated if hasattr(self.user, 'is_authenticated') else 'N/A'}")

        if not self.user or not self.user.is_authenticated:
            logger.warning(f"❌ User not authenticated. Closing connection.")
            logger.warning(f"User: {self.user}, Authenticated: {getattr(self.user, 'is_authenticated', False)}")
            await self.close(code=4001)
            return
        
        logger.info(f"✅ User {self.user.username} authenticated successfully")

        self.message_count = 0
        self.sender = self.user
        
        # Create a personal channel for this user to receive all their messages
        self.user_channel = f"user_{self.user.username}"
        
        logger.info(f"User {self.sender.username} connecting to personal channel {self.user_channel}")

        # Accept WebSocket connection
        await self.accept()

        # Add user to their personal channel
        await self.channel_layer.group_add(
            self.user_channel,
            self.channel_name
        )
        
        # Update user status to online
        cache.set(f"user_status_{self.user.username}", "Online", timeout=None)

        # Get all friends and add this user to their chat rooms
        friends = await self.get_friends_list(self.user)
        
        for friend_username in friends:
            # Create room name for each friend
            usernames = sorted([self.user.username, friend_username])
            room_name = f"chat_{usernames[0]}_{usernames[1]}"
            
            # Join each chat room
            await self.channel_layer.group_add(room_name, self.channel_name)
            
            # Notify friend that this user is online
            await self.channel_layer.group_send(
                f"user_{friend_username}",
                {
                    'type': 'user_status',
                    'username': self.user.username,
                    'status': 'Online',
                }
            )

        # Send friends' online status to this user
        friends_status = await self.get_friends_online_status(self.user)
        await self.send_friends_status(friends_status)

    async def get_user(self):
        """Retrieve user from JWT token in cookies or query string."""
        try:
            # Debug: Log all cookies
            cookies = self.scope.get('cookies', {})
            logger.debug(f"Available cookies: {list(cookies.keys())}")
            
            # Try different cookie names
            token_key = (
                cookies.get('access_token') or 
                cookies.get('access') or 
                cookies.get('token') or
                cookies.get('jwt')
            )

            # Fallback to query string
            if not token_key:
                query_string = self.scope.get("query_string", b"").decode()
                logger.debug(f"Query string: {query_string}")
                query_params = urllib.parse.parse_qs(query_string)
                token_key = query_params.get('token', [None])[0]

            if not token_key:
                logger.warning(f"No access token found. Cookies: {list(cookies.keys())}")
                return AnonymousUser()

            logger.debug(f"Token found: {token_key[:20]}...")
            
            # Validate and decode token
            access_token = AccessToken(token_key)
            
            # Get user from database
            user = await sync_to_async(User.objects.get)(id=access_token['user_id'])
            logger.info(f"User authenticated: {user.username}")
            return user

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            return AnonymousUser()

    @sync_to_async
    def get_friends_list(self, user):
        """Get list of friend usernames."""
        friends = FriendRequest.objects.filter(
            Q(is_accepted=True) & (Q(from_user=user) | Q(to_user=user))
        )
        
        friend_usernames = []
        for friend_request in friends:
            friend = friend_request.to_user if friend_request.from_user == user else friend_request.from_user
            friend_usernames.append(friend.username)
        
        return friend_usernames

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

    async def send_friends_status(self, friends_statuses):
        """Send the online status of all friends to the frontend."""
        await self.send(text_data=json.dumps({
            'type': 'friends_status',
            'friends_statuses': friends_statuses
        }))

    async def user_status(self, event):
        """Handle user status updates."""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'username': event['username'],
            'status': event['status'],
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'user') and hasattr(self, 'user_channel'):
            # Remove from personal channel
            await self.channel_layer.group_discard(self.user_channel, self.channel_name)

            # Update user status to offline
            cache.set(f"user_status_{self.user.username}", "Offline", timeout=None)

            # Notify all friends that this user is offline
            friends = await self.get_friends_list(self.user)
            for friend_username in friends:
                # Notify each friend
                await self.channel_layer.group_send(
                    f"user_{friend_username}",
                    {
                        'type': 'user_status',
                        'username': self.user.username,
                        'status': 'Offline',
                    }
                )
                
                # Leave chat rooms
                usernames = sorted([self.user.username, friend_username])
                room_name = f"chat_{usernames[0]}_{usernames[1]}"
                await self.channel_layer.group_discard(room_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = (data.get('message') or '').strip()
            media = data.get('media')
            typing_status = data.get('typing', False)
            recipient_username = data.get('recipient')  # Get recipient from message data

            if not recipient_username:
                await self.send_error('Recipient username is required')
                return

            # Handle typing indicator
            if 'typing' in data:
                # Create room name
                usernames = sorted([self.sender.username, recipient_username])
                room_name = f"chat_{usernames[0]}_{usernames[1]}"
                
                await self.channel_layer.group_send(
                    room_name,
                    {
                        'type': 'show_typing',
                        'typing': typing_status,
                        'loggedInUser': self.sender.username,
                    }
                )
                return 

            # Validate message or media exists
            if not message and not media:
                await self.send_error('You must send either a message or media')
                return

            # Handle media upload
            media_file = None
            if media:
                media_file = await self.save_media_async(media)
                if not media_file:
                    await self.send_error('Invalid media file')
                    return

            # Get recipient
            recipient = await self.get_recipient_async(recipient_username)
            if not recipient:
                await self.send_error('Recipient does not exist')
                return

            # Save message to database
            message_obj = await self.save_message_async(
                self.sender, recipient, message, media_file
            )

            # Create room name for this chat
            usernames = sorted([self.sender.username, recipient_username])
            room_name = f"chat_{usernames[0]}_{usernames[1]}"

            # Broadcast message to both users in the chat
            await self.channel_layer.group_send(
                room_name,
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

    async def get_room_group_name(self, sender_username, recipient_username):
        return f"{min(sender_username, recipient_username)}_{max(sender_username, recipient_username)}"

    @sync_to_async
    def get_recipient_async(self, recipient_username):
        try:
            return User.objects.get(username=recipient_username)
        except User.DoesNotExist:
            return None