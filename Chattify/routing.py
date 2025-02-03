from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/http://localhost:5173/', ChatConsumer.as_asgi()),
]
