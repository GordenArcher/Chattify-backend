from django.urls import path
from . import views

urlpatterns = [
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path("auth/logout/", views.logout),
    path("users/", views.get_users),
    path("set_profile/", views.set_user_profile),
    path("get_profile/", views.get_profile),
]
