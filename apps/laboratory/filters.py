"""
Filters for laboratory app
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import LabRequest


class LabRequestFilter(filters.FilterSet):
    """Filter for LabRequest model"""
    
    # Patient filters
    patient = filters.NumberFilter(field_name='patient__id')
    patient_name = filters.CharFilter(field_name='patient__first_name', lookup_expr='icontains')
    patient_phone = filters.CharFilter(field_name='patient__phone_primary', lookup_expr='icontains')
    
    # Visit filters
    visit = filters.NumberFilter(field_name='visit__id')
    visit_number = filters.CharFilter(field_name='visit__visit_number', lookup_expr='icontains')
    
    # Test filters
    test = filters.NumberFilter(field_name='test__id')
    test_name = filters.CharFilter(field_name='test__name', lookup_expr='icontains')
    test_category = filters.NumberFilter(field_name='test__category__id')
    specimen_type = filters.CharFilter(field_name='specimen_type', lookup_expr='icontains')
    
    # Doctor filters
    requesting_doctor = filters.NumberFilter(field_name='requesting_doctor__id')
    doctor_name = filters.CharFilter(field_name='requesting_doctor__first_name', lookup_expr='icontains')
    
    # Status and priority
    status = filters.ChoiceFilter(choices=LabRequest.STATUS_CHOICES)
    status_in = filters.MultipleChoiceFilter(field_name='status', choices=LabRequest.STATUS_CHOICES, lookup_expr='in')
    priority = filters.ChoiceFilter(choices=LabRequest.PRIORITY_CHOICES)
    
    # Date filters
    created_from = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_to = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    completed_from = filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_to = filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')
    
    # Result filters
    is_abnormal = filters.BooleanFilter()
    has_result = filters.BooleanFilter(field_name='result_value', lookup_expr='isnull', exclude=True)
    
    # Assigned to
    assigned_to = filters.NumberFilter(field_name='assigned_to__id')
    
    # Search
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = LabRequest
        fields = [
            'id', 'request_number', 'status', 'priority', 'is_abnormal',
            'test', 'patient', 'requesting_doctor', 'assigned_to'
        ]
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(request_number__icontains=value) |
            Q(patient__first_name__icontains=value) |
            Q(patient__last_name__icontains=value) |
            Q(patient__phone_primary__icontains=value) |
            Q(test__name__icontains=value) |
            Q(requesting_doctor__first_name__icontains=value)
        )