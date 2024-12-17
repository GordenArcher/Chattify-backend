from rest_framework import serializers
from .models import Chat, Profile
from django.contrib.auth.models import User

class ChatSerialzer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = '__all__'



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']



class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = "__all__"
