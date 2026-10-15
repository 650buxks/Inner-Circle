from django.contrib import admin

from .models import FriendRequest


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "created_at")
    search_fields = ("from_user__username", "to_user__username")
