from rest_framework import serializers
from .models import Chat, Profile, FriendRequest
from django.contrib.auth.models import User


class UsSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ['id', 'username']

class ChatSerialzer(serializers.ModelSerializer):
    user = UsSerializer()
    recipient = UsSerializer()
    class Meta:
        model = Chat
        fields = ['id', 'user', 'recipient', 'message', 'media', 'sent_at']



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
    from_user = UserSerializer()
    to_user = UserSerializer()
    class Meta:
        model = FriendRequest
        fields = ['id', 'from_user', 'to_user', 'created_at']
