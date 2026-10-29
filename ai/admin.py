from django.contrib import admin

from .models import AIRequest


@admin.register(AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "feature",
        "created_at",
        "input_tokens",
        "output_tokens",
    )
    list_filter = ("feature",)
