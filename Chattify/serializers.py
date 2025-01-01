from rest_framework import serializers
from .models import Chat, Profile, FriendRequest
from django.contrib.auth.models import User

class ChatSerialzer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ['user', 'recipient', 'message', 'media', 'sent_at']




class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user', 'profile_picture', 'cover_picture', 'bio']



class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']


class FriendRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendRequest
        fields = '__all__'
