"""
Filters for triage app
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import Triage


class TriageFilter(filters.FilterSet):
    """Filter for Triage model"""
    
    # Visit filters
    visit = filters.NumberFilter(field_name='visit__id')
    visit_number = filters.CharFilter(field_name='visit__visit_number', lookup_expr='icontains')
    
    # Patient filters
    patient_name = filters.CharFilter(field_name='visit__patient__first_name', lookup_expr='icontains')
    patient_id = filters.NumberFilter(field_name='visit__patient__id')
    
    # Triage officer filters
    triage_officer = filters.NumberFilter(field_name='triage_officer__id')
    triage_officer_name = filters.CharFilter(field_name='triage_officer__first_name', lookup_expr='icontains')
    
    # Priority and score filters
    priority = filters.ChoiceFilter(choices=Triage.PRIORITY_CHOICES)
    priority_in = filters.MultipleChoiceFilter(field_name='priority', choices=Triage.PRIORITY_CHOICES, lookup_expr='in')
    triage_score_min = filters.NumberFilter(field_name='triage_score', lookup_expr='gte')
    triage_score_max = filters.NumberFilter(field_name='triage_score', lookup_expr='lte')
    
    # Vitals filters
    temperature_min = filters.NumberFilter(field_name='temperature', lookup_expr='gte')
    temperature_max = filters.NumberFilter(field_name='temperature', lookup_expr='lte')
    heart_rate_min = filters.NumberFilter(field_name='heart_rate', lookup_expr='gte')
    heart_rate_max = filters.NumberFilter(field_name='heart_rate', lookup_expr='lte')
    systolic_bp_min = filters.NumberFilter(field_name='systolic_bp', lookup_expr='gte')
    systolic_bp_max = filters.NumberFilter(field_name='systolic_bp', lookup_expr='lte')
    oxygen_saturation_min = filters.NumberFilter(field_name='oxygen_saturation', lookup_expr='gte')
    oxygen_saturation_max = filters.NumberFilter(field_name='oxygen_saturation', lookup_expr='lte')
    
    # Date filters
    triage_start_from = filters.DateTimeFilter(field_name='triage_start', lookup_expr='gte')
    triage_start_to = filters.DateTimeFilter(field_name='triage_start', lookup_expr='lte')
    triage_completed_from = filters.DateTimeFilter(field_name='triage_completed', lookup_expr='gte')
    triage_completed_to = filters.DateTimeFilter(field_name='triage_completed', lookup_expr='lte')
    
    # Boolean filters
    is_completed = filters.BooleanFilter(field_name='triage_completed', lookup_expr='isnull', exclude=True)
    is_critical = filters.BooleanFilter(method='filter_critical')
    
    # Search
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Triage
        fields = [
            'id', 'priority', 'triage_score', 'avpu_score', 'pain_score',
            'is_pregnant', 'is_diabetic', 'is_hypertensive', 'is_asthmatic',
            'is_trauma_patient', 'oxygen_given', 'iv_line_placed'
        ]
    
    def filter_critical(self, queryset, name, value):
        """Filter for critical triage cases"""
        if value:
            return queryset.filter(
                Q(priority='resuscitation') |
                Q(triage_score__gte=8) |
                Q(oxygen_saturation__lt=90) |
                Q(glasgow_coma_score__lt=13)
            )
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(visit__visit_number__icontains=value) |
            Q(visit__patient__first_name__icontains=value) |
            Q(visit__patient__last_name__icontains=value) |
            Q(triage_officer__first_name__icontains=value) |
            Q(triage_notes__icontains=value)
        )