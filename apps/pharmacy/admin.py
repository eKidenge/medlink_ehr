from django.contrib import admin
from django.utils.html import format_html
from .models import Medication, Prescription, StockTransaction


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = [
        'drug_code', 'generic_name', 'brand_name', 'category', 'drug_form',
        'current_stock_coloured', 'unit_price', 'is_active'
    ]
    list_filter = ['category', 'drug_form', 'is_active', 'requires_prescription', 'is_controlled']
    search_fields = ['generic_name', 'brand_name', 'drug_code']
    list_editable = ['unit_price', 'is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('drug_code', 'generic_name', 'brand_name', 'category', 'drug_form', 'strength')
        }),
        ('Stock Information', {
            'fields': ('current_stock', 'reorder_level', 'reorder_quantity', 'unit_price')
        }),
        ('Prescription Details', {
            'fields': ('requires_prescription', 'is_controlled')
        }),
        ('Safety Information', {
            'fields': ('common_allergies', 'contraindications', 'side_effects', 'precautions')
        }),
        ('Supply Information', {
            'fields': ('batch_number', 'manufacturer', 'expiry_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    def current_stock_coloured(self, obj):
        if obj.current_stock <= 0:
            colour = '#F44336'
            text = f"{obj.current_stock} (OUT OF STOCK)"
        elif obj.current_stock <= obj.reorder_level:
            colour = '#FF9800'
            text = f"{obj.current_stock} (LOW STOCK)"
        else:
            colour = '#4CAF50'
            text = str(obj.current_stock)
        
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', colour, text)
    current_stock_coloured.short_description = 'Current Stock'
    
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Marked {queryset.count()} medications as active")
    mark_as_active.short_description = "Mark selected as active"
    
    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Marked {queryset.count()} medications as inactive")
    mark_as_inactive.short_description = "Mark selected as inactive"


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = [
        'prescription_number', 'patient_link', 'medication_name', 'dosage',
        'quantity_display', 'status_coloured', 'prescribed_at', 'dispensed_at'
    ]
    list_filter = ['status', 'route', 'prescribed_at', 'dispensed_at']
    search_fields = ['prescription_number', 'patient__first_name', 'patient__last_name']
    readonly_fields = ['prescription_number', 'prescribed_at', 'refills_remaining']
    raw_id_fields = ['patient', 'visit', 'medication', 'prescribing_doctor', 'dispensed_by']
    
    def patient_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:patients_patient_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)
    patient_link.short_description = 'Patient'
    
    def medication_name(self, obj):
        return obj.medication.generic_name
    medication_name.admin_order_field = 'medication__generic_name'
    
    def quantity_display(self, obj):
        return f"{obj.dispensed_quantity}/{obj.quantity}"
    quantity_display.short_description = 'Dispensed/Qty'
    
    def status_coloured(self, obj):
        colours = {
            'pending': '#FF9800',
            'partial': '#2196F3',
            'dispensed': '#4CAF50',
            'cancelled': '#F44336',
            'expired': '#9E9E9E'
        }
        colour = colours.get(obj.status, '#9E9E9E')
        return format_html('<span style="color: {};">{}</span>', colour, obj.get_status_display())
    status_coloured.short_description = 'Status'
    
    actions = ['dispense_selected']
    
    def dispense_selected(self, request, queryset):
        for prescription in queryset.filter(status='pending'):
            try:
                prescription.dispense(prescription.quantity, request.user)
            except:
                pass
        self.message_user(request, f"Dispensed {queryset.count()} prescriptions")
    dispense_selected.short_description = "Dispense selected prescriptions"


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['medication', 'transaction_type', 'quantity', 'stock_before', 'stock_after', 'created_by', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['medication__generic_name', 'reference_number']
    readonly_fields = ['created_at']
    raw_id_fields = ['medication', 'prescription', 'created_by']