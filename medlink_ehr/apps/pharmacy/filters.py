"""
Filters for pharmacy app
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import Prescription, Medication


class PrescriptionFilter(filters.FilterSet):
    """Filter for Prescription model"""
    
    # Patient filters
    patient = filters.NumberFilter(field_name='patient__id')
    patient_name = filters.CharFilter(field_name='patient__first_name', lookup_expr='icontains')
    patient_phone = filters.CharFilter(field_name='patient__phone_primary', lookup_expr='icontains')
    
    # Visit filters
    visit = filters.NumberFilter(field_name='visit__id')
    visit_number = filters.CharFilter(field_name='visit__visit_number', lookup_expr='icontains')
    
    # Medication filters
    medication = filters.NumberFilter(field_name='medication__id')
    medication_name = filters.CharFilter(field_name='medication__generic_name', lookup_expr='icontains')
    medication_category = filters.CharFilter(field_name='medication__category', lookup_expr='icontains')
    
    # Doctor filters
    prescribing_doctor = filters.NumberFilter(field_name='prescribing_doctor__id')
    doctor_name = filters.CharFilter(field_name='prescribing_doctor__first_name', lookup_expr='icontains')
    
    # Status and route
    status = filters.ChoiceFilter(choices=Prescription.STATUS_CHOICES)
    status_in = filters.MultipleChoiceFilter(field_name='status', choices=Prescription.STATUS_CHOICES, lookup_expr='in')
    route = filters.ChoiceFilter(choices=Prescription.ROUTE_CHOICES)
    
    # Date filters
    prescribed_from = filters.DateTimeFilter(field_name='prescribed_at', lookup_expr='gte')
    prescribed_to = filters.DateTimeFilter(field_name='prescribed_at', lookup_expr='lte')
    dispensed_from = filters.DateTimeFilter(field_name='dispensed_at', lookup_expr='gte')
    dispensed_to = filters.DateTimeFilter(field_name='dispensed_at', lookup_expr='lte')
    
    # Quantity filters
    quantity_min = filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    quantity_max = filters.NumberFilter(field_name='quantity', lookup_expr='lte')
    
    # Pending prescriptions
    pending = filters.BooleanFilter(method='filter_pending')
    
    # Search
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'prescription_number', 'status', 'route', 'medication',
            'patient', 'prescribing_doctor', 'dispensed_by'
        ]
    
    def filter_pending(self, queryset, name, value):
        """Filter for pending prescriptions"""
        if value:
            return queryset.filter(status='pending')
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(prescription_number__icontains=value) |
            Q(patient__first_name__icontains=value) |
            Q(patient__last_name__icontains=value) |
            Q(patient__phone_primary__icontains=value) |
            Q(medication__generic_name__icontains=value) |
            Q(prescribing_doctor__first_name__icontains=value)
        )


class MedicationFilter(filters.FilterSet):
    """Filter for Medication model"""
    
    generic_name = filters.CharFilter(lookup_expr='icontains')
    brand_name = filters.CharFilter(lookup_expr='icontains')
    category = filters.ChoiceFilter(choices=Medication.DRUG_CATEGORIES)
    drug_form = filters.ChoiceFilter(choices=Medication.DRUG_FORMS)
    is_active = filters.BooleanFilter()
    requires_prescription = filters.BooleanFilter()
    is_controlled = filters.BooleanFilter()
    
    # Stock filters
    low_stock = filters.BooleanFilter(method='filter_low_stock')
    out_of_stock = filters.BooleanFilter(method='filter_out_of_stock')
    current_stock_min = filters.NumberFilter(field_name='current_stock', lookup_expr='gte')
    current_stock_max = filters.NumberFilter(field_name='current_stock', lookup_expr='lte')
    
    # Price filters
    price_min = filters.NumberFilter(field_name='unit_price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='unit_price', lookup_expr='lte')
    
    # Expiry filters
    expiring_soon = filters.BooleanFilter(method='filter_expiring_soon')
    expired = filters.BooleanFilter(method='filter_expired')
    
    # Search
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Medication
        fields = [
            'id', 'drug_code', 'category', 'drug_form', 'is_active',
            'requires_prescription', 'is_controlled'
        ]
    
    def filter_low_stock(self, queryset, name, value):
        """Filter medications with low stock"""
        if value:
            from django.db.models import F
            return queryset.filter(current_stock__lte=F('reorder_level'))
        return queryset
    
    def filter_out_of_stock(self, queryset, name, value):
        """Filter out of stock medications"""
        if value:
            return queryset.filter(current_stock=0)
        return queryset
    
    def filter_expiring_soon(self, queryset, name, value):
        """Filter medications expiring within 30 days"""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            thirty_days = timezone.now().date() + timedelta(days=30)
            return queryset.filter(
                expiry_date__lte=thirty_days,
                expiry_date__gte=timezone.now().date()
            )
        return queryset
    
    def filter_expired(self, queryset, name, value):
        """Filter expired medications"""
        if value:
            from django.utils import timezone
            return queryset.filter(expiry_date__lt=timezone.now().date())
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(generic_name__icontains=value) |
            Q(brand_name__icontains=value) |
            Q(drug_code__icontains=value) |
            Q(manufacturer__icontains=value)
        )