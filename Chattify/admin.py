from django.contrib import admin
from .models import Chat

# Register your models here.
class ChatAdmin(admin.ModelAdmin):
    list_display = ['user', 'reciepient', 'message', 'media', 'sent_at']
    search_fields = ['user', 'reciepient', 'message', 'media', 'sent_at']



    def __str__(self):
        return f"from {self.user} to {self.reciepient}"
    

admin.site.register(Chat, ChatAdmin)    