"""
Filters for patients app
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import Patient


class PatientFilter(filters.FilterSet):
    """Filter for Patient model"""
    
    # Basic filters
    first_name = filters.CharFilter(lookup_expr='icontains')
    last_name = filters.CharFilter(lookup_expr='icontains')
    full_name = filters.CharFilter(method='filter_full_name')
    patient_number = filters.CharFilter(lookup_expr='icontains')
    mrn_number = filters.CharFilter(lookup_expr='icontains')
    
    # Contact filters
    phone = filters.CharFilter(field_name='phone_primary', lookup_expr='icontains')
    email = filters.CharFilter(lookup_expr='icontains')
    
    # Demographic filters
    gender = filters.ChoiceFilter(choices=Patient.GENDER_CHOICES)
    county = filters.CharFilter(lookup_expr='icontains')
    blood_type = filters.ChoiceFilter(choices=Patient.BLOOD_TYPE)
    marital_status = filters.ChoiceFilter(choices=Patient.MARITAL_STATUS)
    
    # Identification filters
    national_id = filters.CharFilter(field_name='identification_number', lookup_expr='icontains')
    nhif_number = filters.CharFilter(lookup_expr='icontains')
    
    # Age filters
    age_min = filters.NumberFilter(field_name='age', lookup_expr='gte')
    age_max = filters.NumberFilter(field_name='age', lookup_expr='lte')
    date_of_birth_from = filters.DateFilter(field_name='date_of_birth', lookup_expr='lte')
    date_of_birth_to = filters.DateFilter(field_name='date_of_birth', lookup_expr='gte')
    
    # Date filters
    created_at_from = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_to = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Boolean filters
    is_active = filters.BooleanFilter()
    has_allergies = filters.BooleanFilter()
    has_chronic_diseases = filters.BooleanFilter()
    is_pregnant = filters.BooleanFilter()
    is_deceased = filters.BooleanFilter()
    is_disabled = filters.BooleanFilter()
    
    # Search across multiple fields
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Patient
        fields = [
            'id', 'patient_number', 'mrn_number', 'gender', 'county',
            'blood_type', 'marital_status', 'is_active', 'has_allergies',
            'has_chronic_diseases', 'is_pregnant', 'is_deceased'
        ]
    
    def filter_full_name(self, queryset, name, value):
        """Filter by full name"""
        return queryset.filter(
            Q(first_name__icontains=value) |
            Q(middle_name__icontains=value) |
            Q(last_name__icontains=value)
        )
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(patient_number__icontains=value) |
            Q(mrn_number__icontains=value) |
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(phone_primary__icontains=value) |
            Q(identification_number__icontains=value) |
            Q(nhif_number__icontains=value) |
            Q(email__icontains=value)
        )