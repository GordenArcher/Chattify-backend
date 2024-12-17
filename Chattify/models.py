from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='sender')
    reciepient = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='reciepient')
    message = models.TextField(blank=True, null=True)
    media = models.FileField(upload_to='message_images/', blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)



class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profile_image", null=True, blank=True)
    cover_picture = models.ImageField(upload_to="cover_image", null=True, blank=True)
    bio = models.TextField(max_length=1000, null=True, blank=True)