from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # URL pattern for WebSocket connection
    re_path(r'ws/chat/(?P<username>\w+)/(?P<recipient>\w+)?$', consumers.ChatConsumer.as_asgi()),
    # URL pattern for WebSocket connection with just the logged-in user's username
    re_path(r'ws/chat/(?P<username>\w+)$', consumers.ChatConsumer.as_asgi()),
]
