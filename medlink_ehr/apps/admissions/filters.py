"""
Filters for admissions app
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import Admission, Ward


class AdmissionFilter(filters.FilterSet):
    """Filter for Admission model"""
    
    # Patient filters
    patient = filters.NumberFilter(field_name='patient__id')
    patient_name = filters.CharFilter(field_name='patient__first_name', lookup_expr='icontains')
    patient_phone = filters.CharFilter(field_name='patient__phone_primary', lookup_expr='icontains')
    
    # Ward and bed filters
    ward = filters.NumberFilter(field_name='ward__id')
    ward_name = filters.CharFilter(field_name='ward__name', lookup_expr='icontains')
    bed = filters.NumberFilter(field_name='bed__id')
    bed_number = filters.CharFilter(field_name='bed__bed_number', lookup_expr='icontains')
    
    # Doctor filters
    admitting_doctor = filters.NumberFilter(field_name='admitting_doctor__id')
    doctor_name = filters.CharFilter(field_name='admitting_doctor__first_name', lookup_expr='icontains')
    
    # Status filters
    status = filters.ChoiceFilter(choices=Admission.STATUS_CHOICES)
    status_in = filters.MultipleChoiceFilter(field_name='status', choices=Admission.STATUS_CHOICES, lookup_expr='in')
    admission_type = filters.ChoiceFilter(choices=Admission.ADMISSION_TYPE)
    discharge_status = filters.ChoiceFilter(choices=Admission.DISCHARGE_STATUS)
    
    # Date filters
    admission_date_from = filters.DateFilter(field_name='admission_date', lookup_expr='date__gte')
    admission_date_to = filters.DateFilter(field_name='admission_date', lookup_expr='date__lte')
    discharge_date_from = filters.DateFilter(field_name='discharge_date', lookup_expr='date__gte')
    discharge_date_to = filters.DateFilter(field_name='discharge_date', lookup_expr='date__lte')
    
    # Length of stay filters
    los_min = filters.NumberFilter(method='filter_los_min')
    los_max = filters.NumberFilter(method='filter_los_max')
    
    # Current admissions (not discharged)
    current = filters.BooleanFilter(method='filter_current')
    
    # Search
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Admission
        fields = [
            'id', 'admission_number', 'status', 'admission_type',
            'discharge_status', 'ward', 'bed'
        ]
    
    def filter_current(self, queryset, name, value):
        """Filter for current admissions (not discharged)"""
        if value:
            return queryset.filter(status__in=['admitted', 'in_treatment', 'stable', 'critical'])
        return queryset
    
    def filter_los_min(self, queryset, name, value):
        """Filter by minimum length of stay"""
        from django.db.models import F, ExpressionWrapper, fields
        from datetime import timedelta
        
        queryset = queryset.annotate(
            los=ExpressionWrapper(
                F('discharge_date') - F('admission_date'),
                output_field=fields.DurationField()
            )
        )
        return queryset.filter(los__gte=timedelta(days=value))
    
    def filter_los_max(self, queryset, name, value):
        """Filter by maximum length of stay"""
        from django.db.models import F, ExpressionWrapper, fields
        from datetime import timedelta
        
        queryset = queryset.annotate(
            los=ExpressionWrapper(
                F('discharge_date') - F('admission_date'),
                output_field=fields.DurationField()
            )
        )
        return queryset.filter(los__lte=timedelta(days=value))
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(admission_number__icontains=value) |
            Q(patient__first_name__icontains=value) |
            Q(patient__last_name__icontains=value) |
            Q(patient__phone_primary__icontains=value) |
            Q(ward__name__icontains=value) |
            Q(primary_diagnosis__icontains=value)
        )


class WardFilter(filters.FilterSet):
    """Filter for Ward model"""
    
    name = filters.CharFilter(lookup_expr='icontains')
    ward_type = filters.ChoiceFilter(choices=Ward.WARD_TYPES)
    is_active = filters.BooleanFilter()
    has_available_beds = filters.BooleanFilter(method='filter_has_available_beds')
    
    class Meta:
        model = Ward
        fields = ['id', 'name', 'ward_type', 'is_active']
    
    def filter_has_available_beds(self, queryset, name, value):
        """Filter wards with available beds"""
        if value:
            return queryset.filter(available_beds__gt=0)
        return queryset