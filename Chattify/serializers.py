from rest_framework import serializers
from .models import Chat

class ChatSerialzer(serializers.ModelField):
    class Meta:
        model = Chat
        fields = '__all__'