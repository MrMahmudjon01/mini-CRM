import django_filters

from .models import Lead


class LeadFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Lead.Status.choices)
    source = django_filters.ChoiceFilter(choices=Lead.Source.choices)
    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Lead
        fields = ["status", "source", "created_from", "created_to"]
