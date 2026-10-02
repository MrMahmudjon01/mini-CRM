import re

from rest_framework import serializers

from .models import Activity, Lead

PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{5,18}[0-9]$")


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ["id", "name", "phone", "email", "source", "note", "status",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        return value

    def validate_phone(self, value):
        value = value.strip()
        if value and not PHONE_RE.match(value):
            raise serializers.ValidationError(
                "Enter a valid phone number, e.g. +998901234567."
            )
        return value

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        # A lead needs at least one way to be contacted. For partial updates,
        # fall back to the stored value for the field that was not sent.
        def current(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, "") if self.instance else ""

        if not current("phone") and not current("email"):
            raise serializers.ValidationError("Provide at least a phone number or an email.")
        return attrs


class LeadStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Lead.Status.choices)


class ActivitySerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.username", default=None, read_only=True)

    class Meta:
        model = Activity
        fields = ["id", "action", "message", "actor", "created_at"]
