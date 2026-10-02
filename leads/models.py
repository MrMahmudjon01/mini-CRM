from django.conf import settings
from django.db import models


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    class Source(models.TextChoices):
        WEBSITE = "website", "Website"
        TELEGRAM = "telegram", "Telegram"
        INSTAGRAM = "instagram", "Instagram"
        REFERRAL = "referral", "Referral"
        PHONE = "phone", "Phone call"
        OTHER = "other", "Other"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leads"
    )
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.OTHER)
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"


class Activity(models.Model):
    """Append-only history of what happened to a lead."""

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        STATUS_CHANGED = "status_changed", "Status changed"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "activities"

    def __str__(self):
        return f"{self.lead_id}: {self.message}"
