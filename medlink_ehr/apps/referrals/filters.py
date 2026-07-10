"""
Filters for referrals app
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import Referral


class ReferralFilter(filters.FilterSet):
    """Filter for Referral model"""
    
    # Patient filters
    patient = filters.NumberFilter(field_name='patient__id')
    patient_name = filters.CharFilter(field_name='patient__first_name', lookup_expr='icontains')
    patient_phone = filters.CharFilter(field_name='patient__phone_primary', lookup_expr='icontains')
    
    # Visit filters
    visit = filters.NumberFilter(field_name='visit__id')
    visit_number = filters.CharFilter(field_name='visit__visit_number', lookup_expr='icontains')
    
    # Doctor filters
    referring_doctor = filters.NumberFilter(field_name='referring_doctor__id')
    doctor_name = filters.CharFilter(field_name='referring_doctor__first_name', lookup_expr='icontains')
    
    # Referral details
    referral_type = filters.ChoiceFilter(choices=Referral.REFERRAL_TYPE)
    status = filters.ChoiceFilter(choices=Referral.STATUS_CHOICES)
    status_in = filters.MultipleChoiceFilter(field_name='status', choices=Referral.STATUS_CHOICES, lookup_expr='in')
    priority = filters.ChoiceFilter(choices=Referral.PRIORITY_CHOICES)
    
    # Facility filters
    referring_facility = filters.CharFilter(lookup_expr='icontains')
    receiving_facility = filters.CharFilter(lookup_expr='icontains')
    receiving_department = filters.CharFilter(lookup_expr='icontains')
    receiving_doctor = filters.CharFilter(lookup_expr='icontains')
    
    # Date filters
    created_from = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_to = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    completed_from = filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_to = filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')
    
    # Follow-up
    follow_up_required = filters.BooleanFilter()
    follow_up_date_from = filters.DateFilter(field_name='follow_up_date', lookup_expr='gte')
    follow_up_date_to = filters.DateFilter(field_name='follow_up_date', lookup_expr='lte')
    
    # Pending referrals
    pending = filters.BooleanFilter(method='filter_pending')
    
    # Search
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Referral
        fields = [
            'id', 'referral_number', 'referral_type', 'status', 'priority',
            'patient', 'referring_doctor', 'receiving_facility'
        ]
    
    def filter_pending(self, queryset, name, value):
        """Filter for pending referrals"""
        if value:
            return queryset.filter(status='pending')
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(referral_number__icontains=value) |
            Q(patient__first_name__icontains=value) |
            Q(patient__last_name__icontains=value) |
            Q(receiving_facility__icontains=value) |
            Q(reason_for_referral__icontains=value) |
            Q(provisional_diagnosis__icontains=value)
        )