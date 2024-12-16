from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='sender')
    reciepient = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='reciepient')
    message = models.TextField(blank=True, null=True)
    media = models.FileField(upload_to='message_images/', blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)