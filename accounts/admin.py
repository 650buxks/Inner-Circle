from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CliqueUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Profile",
            {
                "fields": (
                    "display_name",
                    "bio",
                    "status_message",
                    "last_seen",
                    "ai_opt_out",
                    "smart_replies_on",
                    "friend_requests_from",
                )
            },
        ),
        ("Friends", {"fields": ("friends", "blocked_users")}),
    )
    filter_horizontal = UserAdmin.filter_horizontal + (
        "friends",
        "blocked_users",
    )
