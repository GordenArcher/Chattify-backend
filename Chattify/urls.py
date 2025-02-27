from django.urls import path
from . import views
from .views import customTokenRefreshView

urlpatterns = [
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path("refresh/", customTokenRefreshView.as_view(), name="custom_refresh"),
    path("auth/logout/", views.logout),
    path("isAuthenticated/", views.protected_view),
    path("users/", views.get_users),
    path("set_profile/", views.set_user_profile),
    path("get_profile/", views.get_profile),
    path("chat_messages/<str:username>/", views.chat_message),
    path("send_request/<str:id>/", views.send_friend_request),
    path("recieved_request/", views.recieved_request),
    path("friends/", views.friends),
    path('accept-friend-request/<int:request_id>/', views.accept_friend_request,),
    path('reject-friend-request/<int:request_id>/', views.reject_friend_request),
]
