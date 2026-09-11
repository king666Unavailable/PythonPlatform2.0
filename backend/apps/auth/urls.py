"""Authentication API routes."""

from django.urls import path

from .views import csrf_token, login, logout, me, password_change


urlpatterns = [
    path("login", login, name="login"),
    path("password-change", password_change, name="password-change"),
    path("csrf", csrf_token, name="csrf"),
    path("me", me, name="me"),
    path("logout", logout, name="logout"),
]
