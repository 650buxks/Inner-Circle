from django.contrib import admin

from .models import Conversation, Membership, Message


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "kind", "last_activity_at")
    list_filter = ("kind",)
    inlines = [MembershipInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "sender",
        "conversation",
        "kind",
        "created_at",
        "is_deleted",
    )
    list_filter = ("kind", "is_deleted")
    search_fields = ("body",)
