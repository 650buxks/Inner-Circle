from django.urls import path

from . import views

app_name = "chats"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/", views.chat_detail, name="detail"),
    path("<int:pk>/send/", views.send, name="send"),
    path("start/<str:username>/", views.start_chat, name="start"),
    path("messages/<int:pk>/edit/", views.edit, name="edit"),
    path("messages/<int:pk>/delete/", views.delete, name="delete"),
]
