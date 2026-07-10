from django.contrib import admin
from django.utils.html import format_html
from .models import LabTestCategory, LabTest, LabRequest, LabResult


@admin.register(LabTestCategory)
class LabTestCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'specimen_type', 'turnaround_time', 'cost', 'is_active']
    list_filter = ['category', 'specimen_type', 'is_active', 'requires_fasting']
    search_fields = ['name', 'code']
    list_editable = ['cost', 'turnaround_time']


@admin.register(LabRequest)
class LabRequestAdmin(admin.ModelAdmin):
    list_display = [
        'request_number', 'patient_link', 'test_name', 'priority_coloured',
        'status_coloured', 'requesting_doctor', 'created_at', 'is_abnormal_flag'
    ]
    list_filter = ['status', 'priority', 'is_abnormal', 'created_at']
    search_fields = ['request_number', 'patient__first_name', 'patient__last_name']
    readonly_fields = ['request_number', 'created_at', 'updated_at']
    raw_id_fields = ['patient', 'visit', 'test', 'requesting_doctor', 'assigned_to', 'verified_by']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_number', 'patient', 'visit', 'test', 'priority')
        }),
        ('Clinical Information', {
            'fields': ('requesting_doctor', 'clinical_notes', 'diagnosis')
        }),
        ('Specimen', {
            'fields': ('specimen_type', 'specimen_collected_at', 'specimen_collected_by', 'specimen_quality')
        }),
        ('Processing', {
            'fields': ('assigned_to', 'started_processing_at', 'completed_at')
        }),
        ('Results', {
            'fields': ('result_value', 'result_numeric', 'reference_range', 'interpretation', 'is_abnormal')
        }),
        ('Verification', {
            'fields': ('verified_by', 'verified_at')
        }),
        ('Status', {
            'fields': ('status', 'rejection_reason', 'rejected_by')
        })
    )
    
    def patient_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:patients_patient_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)
    patient_link.short_description = 'Patient'
    
    def test_name(self, obj):
        return obj.test.name
    test_name.admin_order_field = 'test__name'
    
    def priority_coloured(self, obj):
        colours = {'stat': '#F44336', 'urgent': '#FF9800', 'routine': '#4CAF50'}
        colour = colours.get(obj.priority, '#9E9E9E')
        return format_html('<span style="color: {};">{}</span>', colour, obj.get_priority_display())
    priority_coloured.short_description = 'Priority'
    
    def status_coloured(self, obj):
        colours = {
            'pending': '#FF9800', 'collected': '#2196F3', 'processing': '#9C27B0',
            'verified': '#4CAF50', 'completed': '#4CAF50', 'cancelled': '#F44336', 'rejected': '#F44336'
        }
        colour = colours.get(obj.status, '#9E9E9E')
        return format_html('<span style="color: {};">{}</span>', colour, obj.get_status_display())
    status_coloured.short_description = 'Status'
    
    def is_abnormal_flag(self, obj):
        if obj.is_abnormal:
            return format_html('<span style="color: red; font-weight: bold;">⚠ Abnormal</span>')
        return '-'
    is_abnormal_flag.short_description = 'Abnormal'
    
    actions = ['mark_as_processing', 'verify_selected']
    
    def mark_as_processing(self, request, queryset):
        queryset.filter(status='collected').update(status='processing')
        self.message_user(request, f"Marked {queryset.count()} requests as processing")
    mark_as_processing.short_description = "Mark selected as processing"
    
    def verify_selected(self, request, queryset):
        queryset.filter(status='processing').update(status='verified', verified_by=request.user, verified_at=timezone.now())
        self.message_user(request, f"Verified {queryset.count()} requests")
    verify_selected.short_description = "Verify selected results"


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ['lab_request', 'component_name', 'result_value', 'is_abnormal', 'created_at']
    list_filter = ['is_abnormal']
    search_fields = ['component_name', 'lab_request__request_number']
    raw_id_fields = ['lab_request']