from datetime import timedelta

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import LeadFilter
from .models import Activity, Lead
from .serializers import ActivitySerializer, LeadSerializer, LeadStatusSerializer

TRACKED_FIELDS = ("name", "phone", "email", "source", "note", "status")


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("search", str, description="Search in name, phone, email, note"),
            OpenApiParameter("ordering", str,
                             description="created_at, updated_at, name, status (prefix with - for desc)"),
        ]
    )
)
class LeadViewSet(viewsets.ModelViewSet):
    """CRUD for leads. Every user only sees and manages their own leads."""

    serializer_class = LeadSerializer
    filterset_class = LeadFilter
    search_fields = ["name", "phone", "email", "note"]
    ordering_fields = ["created_at", "updated_at", "name", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Lead.objects.filter(owner=self.request.user)

    # -- helpers -----------------------------------------------------------
    def _log(self, lead, action_, message):
        Activity.objects.create(
            lead=lead, actor=self.request.user, action=action_, message=message
        )

    # -- create / update with activity log ---------------------------------
    @transaction.atomic
    def perform_create(self, serializer):
        lead = serializer.save(owner=self.request.user)
        self._log(lead, Activity.Action.CREATED, f"Lead created with status {lead.get_status_display()}")

    @transaction.atomic
    def perform_update(self, serializer):
        before = {f: getattr(serializer.instance, f) for f in TRACKED_FIELDS}
        old_status_label = serializer.instance.get_status_display()
        lead = serializer.save()
        changed = [f for f in TRACKED_FIELDS if before[f] != getattr(lead, f)]
        if "status" in changed:
            self._log(lead, Activity.Action.STATUS_CHANGED,
                      f"Status changed from {old_status_label} to {lead.get_status_display()}")
        other = [f for f in changed if f != "status"]
        if other:
            self._log(lead, Activity.Action.UPDATED, "Updated: " + ", ".join(other))

    # -- extra endpoints ---------------------------------------------------
    @extend_schema(request=LeadStatusSerializer, responses=LeadSerializer)
    @action(detail=True, methods=["post"], url_path="status",
            serializer_class=LeadStatusSerializer)
    @transaction.atomic
    def change_status(self, request, pk=None):
        lead = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        if new_status != lead.status:
            old_label = lead.get_status_display()
            lead.status = new_status
            lead.save(update_fields=["status", "updated_at"])
            self._log(lead, Activity.Action.STATUS_CHANGED,
                      f"Status changed from {old_label} to {lead.get_status_display()}")
        return Response(LeadSerializer(lead).data)

    @extend_schema(responses=ActivitySerializer(many=True))
    @action(detail=True, methods=["get"], pagination_class=None)
    def activities(self, request, pk=None):
        lead = self.get_object()
        return Response(ActivitySerializer(lead.activities.select_related("actor")[:100], many=True).data)

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=["get"], filter_backends=[], pagination_class=None)
    def stats(self, request):
        qs = self.get_queryset()
        by_status = {s: 0 for s in Lead.Status.values}
        for row in qs.values("status").annotate(c=Count("id")):
            by_status[row["status"]] = row["c"]
        by_source = {s: 0 for s in Lead.Source.values}
        for row in qs.values("source").annotate(c=Count("id")):
            by_source[row["source"]] = row["c"]
        total = sum(by_status.values())
        won = by_status[Lead.Status.WON]
        return Response({
            "total": total,
            "by_status": by_status,
            "by_source": by_source,
            "new_last_7_days": qs.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
            "conversion_rate": round(won / total * 100, 1) if total else 0.0,
        })
