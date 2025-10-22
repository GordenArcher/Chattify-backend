from django.urls import path
from . import views
from .views import customTokenRefreshView

urlpatterns = [
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path('auth/google-login/', views.google_login),
    path('auth/google-register/', views.google_register),
    path("auth/refresh/", customTokenRefreshView.as_view(), name="custom_refresh"),
    path("auth/logout/", views.logout),
    path("isAuthenticated/", views.protected_view),
    path("users/", views.get_users),
    path("set_profile/", views.set_user_profile),
    path("get_profile/", views.get_profile),
    path("chat_messages/<str:username>/", views.chat_message),
    path("get_messages/", views.get_friends_and_messages),
    path("send_request/<str:username>/", views.send_friend_request),
    path("recieved_request/", views.pending_friend_requests),
    path("friends/", views.friends),
    path('accept-friend-request/<str:username>/', views.accept_friend_request,),
    path('reject-friend-request/<str:username>/', views.reject_friend_request),
]
