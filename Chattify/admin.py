from django.contrib import admin
from .models import Chat

# Register your models here.
class ChatAdmin(admin.ModelAdmin):
    list_display = ['user', 'reciepient_user', 'message', 'media', 'sent_at']
    search_fields = ['user', 'reciepient_user', 'message', 'media', 'sent_at']



    def __str__(self):
        return f"from {self.user} to {self.reciepient_user}"
    

admin.site.register(Chat, ChatAdmin)    