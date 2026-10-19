from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/chats/<int:pk>/", consumers.ChatConsumer.as_asgi()),
    path("ws/inbox/", consumers.InboxConsumer.as_asgi()),
]
