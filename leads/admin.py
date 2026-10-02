from django.contrib import admin

from .models import Activity, Lead


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    readonly_fields = ["actor", "action", "message", "created_at"]
    can_delete = False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "email", "source", "status", "owner", "created_at"]
    list_filter = ["status", "source"]
    search_fields = ["name", "phone", "email"]
    inlines = [ActivityInline]
