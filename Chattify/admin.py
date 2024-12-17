from django.contrib import admin
from .models import Chat, Profile

# Register your models here.
class ChatAdmin(admin.ModelAdmin):
    list_display = ['user', 'reciepient', 'message', 'media', 'sent_at']
    search_fields = ['user', 'reciepient', 'message', 'media', 'sent_at']

    def __str__(self):
        return f"from {self.user} to {self.reciepient}"
    


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'profile_picture', 'cover_picture', 'bio']
    search_fields = ['user','profile_picture', 'cover_picture', 'bio']

    

admin.site.register(Chat, ChatAdmin)    
admin.site.register(Profile, ProfileAdmin)    