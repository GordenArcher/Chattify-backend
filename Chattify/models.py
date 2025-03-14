from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='sender')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='recipient')
    message = models.TextField(blank=True, null=True)
    media = models.FileField(upload_to='message_images/', blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~models.Q(user=models.F('recipient')),
                name='prevent_self_message'
            )
        ]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True, related_name="profile")
    profile_picture = models.ImageField(upload_to="profile_image", null=True, blank=True)
    cover_picture = models.ImageField(upload_to="cover_image", null=True, blank=True)
    bio = models.TextField(max_length=1000, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    social_links = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.ip_address} ({self.city}, {self.country})"


class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name="sent_requests", on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name="received_requests", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.from_user} to {self.to_user}"
    
    def accept(self):
        self.is_accepted = True
        self.save()

    def reject(self):
        self.is_rejected = True
        self.save()
