from django.urls import path

from . import views

app_name = "chats"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/", views.chat_detail, name="detail"),
    path("start/<str:username>/", views.start_chat, name="start"),
]
