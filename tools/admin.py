from django.contrib import admin
from .models import Feedback, Suggestion


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("feature", "issue", "submitted_at")
    ordering = ("-submitted_at",)
    readonly_fields = ("submitted_at",)


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("description", "why_needed", "submitted_at")
    ordering = ("-submitted_at",)
    readonly_fields = ("submitted_at",)
