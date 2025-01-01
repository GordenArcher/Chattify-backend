from django.contrib import admin
from .models import Chat, Profile, FriendRequest

# Register your models here.
class ChatAdmin(admin.ModelAdmin):
    list_display = ['user', 'recipient', 'message', 'media', 'sent_at']
    search_fields = ['user', 'recipient', 'message', 'media', 'sent_at']

    def __str__(self):
        return f"from {self.user} to {self.recipient}"
    


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'profile_picture', 'cover_picture', 'bio']
    search_fields = ['user','profile_picture', 'cover_picture', 'bio']



class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'created_at', 'is_accepted', 'is_rejected']
    search_fields = ['from_user', 'to_user', 'created_at', 'is_accepted', 'is_rejected']


    

admin.site.register(Chat, ChatAdmin)    
admin.site.register(Profile, ProfileAdmin)    
admin.site.register(FriendRequest, FriendRequestAdmin)    