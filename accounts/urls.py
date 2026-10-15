from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.CliqueLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.edit_profile, name="edit_profile"),
    path("u/<str:username>/", views.profile, name="profile"),
    path("settings/", views.account_settings, name="settings"),
    path("settings/email/", views.change_email, name="change_email"),
    path("settings/password/", views.change_password, name="change_password"),
    path("settings/ai/", views.update_ai_settings, name="ai_settings"),
    path("settings/delete/", views.delete_account, name="delete_account"),
]
