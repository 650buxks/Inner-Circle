"""The WebSocket side of a chat page.

A consumer is like a view, but for a connection that stays open: one
instance lives for as long as the browser tab has the chat open.
"""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.template.loader import render_to_string

from .models import Conversation, Message
from .realtime import group_name
from .services import (
    ChatError,
    is_member,
    mark_read,
    read_receipt,
    send_message,
)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.chat_id = self.scope["url_route"]["kwargs"]["pk"]
        self.chat = await self.get_chat()
        if self.chat is None:
            # Logged out, or not in this chat: refuse the connection.
            await self.close()
            return
        self.group = group_name(self.chat_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(
                self.group,
                self.channel_name,
            )

    # --- From the browser -------------------------------------------------

    async def receive_json(self, content):
        if content.get("type") == "typing":
            # Not saved anywhere: just passed on to everyone else.
            await self.channel_layer.group_send(
                self.group,
                {
                    "type": "user.typing",
                    "user_id": self.user.pk,
                    "name": self.user.name,
                },
            )
            return
        if content.get("type") != "message":
            return
        body = str(content.get("body", ""))
        try:
            await database_sync_to_async(send_message)(
                self.user,
                self.chat,
                body,
            )
        except ChatError as error:
            await self.send_json({"type": "error", "message": str(error)})

    # --- From the channel layer (see realtime.py) ------------------------

    async def message_new(self, event):
        html = await self.render(event["message_id"], mark_as_read=True)
        if html:
            await self.send_json({"type": "message.new", "html": html})

    async def message_changed(self, event):
        html = await self.render(event["message_id"])
        if html:
            await self.send_json(
                {
                    "type": "message.changed",
                    "id": event["message_id"],
                    "html": html,
                }
            )

    async def user_typing(self, event):
        # Don't tell people that they themselves are typing.
        if event["user_id"] != self.user.pk:
            await self.send_json({"type": "typing", "name": event["name"]})

    async def chat_read(self, event):
        text = await database_sync_to_async(read_receipt)(
            self.chat,
            self.user,
        )
        await self.send_json({"type": "receipt", "text": text})

    # --- Database helpers (Django's ORM is synchronous) -------------------

    @database_sync_to_async
    def get_chat(self):
        if not self.user.is_authenticated:
            return None
        chat = Conversation.objects.filter(pk=self.chat_id).first()
        if chat is None or not is_member(self.user, chat):
            return None
        return chat

    @database_sync_to_async
    def render(self, message_id, mark_as_read=False):
        """The message as HTML, drawn for this user (their own messages
        go on the right)."""
        message = (
            Message.objects.select_related("sender")
            .filter(pk=message_id, conversation_id=self.chat_id)
            .first()
        )
        if message is None or not is_member(self.user, self.chat):
            return None
        if mark_as_read:
            # They're looking at the chat, so the message isn't unread.
            mark_read(self.user, self.chat)
        return render_to_string(
            "chats/_message.html",
            {"message": message, "user": self.user},
        )
