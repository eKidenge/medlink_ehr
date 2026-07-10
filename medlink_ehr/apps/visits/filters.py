"""
Filters for visits app
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import Visit


class VisitFilter(filters.FilterSet):
    """Filter for Visit model"""
    
    # Date filters
    registration_date = filters.DateFilter(field_name='registration_time', lookup_expr='date')
    registration_date_from = filters.DateFilter(field_name='registration_time', lookup_expr='date__gte')
    registration_date_to = filters.DateFilter(field_name='registration_time', lookup_expr='date__lte')
    created_at_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Status filters
    status = filters.ChoiceFilter(choices=Visit.STATUS_CHOICES)
    status_not = filters.ChoiceFilter(field_name='status', lookup_expr='ne', choices=Visit.STATUS_CHOICES)
    status_in = filters.MultipleChoiceFilter(field_name='status', choices=Visit.STATUS_CHOICES, lookup_expr='in')
    
    # Priority filters
    priority = filters.ChoiceFilter(choices=Visit.PRIORITY_CHOICES)
    priority_in = filters.MultipleChoiceFilter(field_name='priority', choices=Visit.PRIORITY_CHOICES, lookup_expr='in')
    
    # Patient filters
    patient = filters.NumberFilter(field_name='patient__id')
    patient_name = filters.CharFilter(field_name='patient__first_name', lookup_expr='icontains')
    patient_phone = filters.CharFilter(field_name='patient__phone_primary', lookup_expr='icontains')
    patient_nhif = filters.CharFilter(field_name='patient__nhif_number', lookup_expr='icontains')
    
    # Doctor filters
    doctor = filters.NumberFilter(field_name='primary_doctor__id')
    doctor_name = filters.CharFilter(field_name='primary_doctor__first_name', lookup_expr='icontains')
    
    # Visit type
    visit_type = filters.ChoiceFilter(choices=Visit.VISIT_TYPE)
    
    # Payment status
    payment_status = filters.ChoiceFilter(choices=Visit.PAYMENT_STATUS)
    
    # Range filters
    total_amount_min = filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    total_amount_max = filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    waiting_time_min = filters.NumberFilter(field_name='total_waiting_time', lookup_expr='gte')
    waiting_time_max = filters.NumberFilter(field_name='total_waiting_time', lookup_expr='lte')
    
    # Boolean filters
    is_emergency = filters.BooleanFilter(field_name='is_emergency')
    requires_admission = filters.BooleanFilter(field_name='requires_admission')
    requires_referral = filters.BooleanFilter(field_name='requires_referral')
    is_telemedicine = filters.BooleanFilter(field_name='is_telemedicine')
    follow_up_required = filters.BooleanFilter(field_name='follow_up_required')
    
    # Search across multiple fields
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Visit
        fields = [
            'id', 'visit_number', 'status', 'priority', 'visit_type',
            'payment_status', 'is_emergency', 'requires_admission',
            'requires_referral', 'follow_up_required'
        ]
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(visit_number__icontains=value) |
            Q(patient__first_name__icontains=value) |
            Q(patient__last_name__icontains=value) |
            Q(patient__phone_primary__icontains=value) |
            Q(patient__identification_number__icontains=value) |
            Q(primary_doctor__first_name__icontains=value) |
            Q(primary_doctor__last_name__icontains=value) |
            Q(chief_complaint__icontains=value) |
            Q(final_diagnosis__icontains=value)
        )