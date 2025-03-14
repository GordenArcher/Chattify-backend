from django.urls import path
from . import views
from .views import customTokenRefreshView

urlpatterns = [
    path("v1/auth/register/", views.register),
    path("v1/auth/login/", views.login),
    path('v1/auth/google-login/', views.google_login),
    path('v1/auth/google-register/', views.google_register),
    path("v1/auth/refresh/", customTokenRefreshView.as_view(), name="custom_refresh"),
    path("v1/auth/logout/", views.logout),
    path("v1/isAuthenticated/", views.protected_view),
    path("v1/users/", views.get_users),
    path("v1/set_profile/", views.set_user_profile),
    path("v1/get_profile/", views.get_profile),
    path("v1/chat_messages/<str:username>/", views.chat_message),
    path("v1/get_messages/", views.get_friends_and_messages),
    path("v1/send_request/<str:id>/", views.send_friend_request),
    path("v1/recieved_request/", views.recieved_request),
    path("v1/friends/", views.friends),
    path('v1/accept-friend-request/<int:request_id>/', views.accept_friend_request,),
    path('v1/reject-friend-request/<int:request_id>/', views.reject_friend_request),
]
