from django.contrib import admin
from django.utils.html import format_html
from .models import Triage, TriageQueue


@admin.register(Triage)
class TriageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'visit_link', 'patient_name', 'priority_coloured', 
        'triage_score', 'triage_officer', 'triage_start', 'completed_status'
    ]
    list_filter = ['priority', 'triage_completed', 'triage_start']
    search_fields = ['visit__visit_number', 'visit__patient__first_name', 'visit__patient__last_name']
    readonly_fields = ['triage_score', 'colour_code', 'triage_start']
    raw_id_fields = ['visit', 'triage_officer', 'completed_by']
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('visit', 'triage_officer')
        }),
        ('Vital Signs', {
            'fields': ('temperature', 'heart_rate', 'respiratory_rate', 'systolic_bp', 
                      'diastolic_bp', 'oxygen_saturation', 'blood_glucose')
        }),
        ('Neurological Assessment', {
            'fields': ('avpu_score', 'glasgow_coma_score', 'pupil_response')
        }),
        ('Pain Assessment', {
            'fields': ('pain_score', 'pain_location')
        }),
        ('Physical Examination', {
            'fields': ('breathing_difficulty', 'breath_sounds', 'use_accessory_muscles',
                      'capillary_refill', 'peripheral_pulses', 'skin_turgor',
                      'rash', 'rash_description', 'bruises', 'swelling', 'swelling_location')
        }),
        ('Risk Factors', {
            'fields': ('is_pregnant', 'pregnancy_weeks', 'is_diabetic', 'is_hypertensive',
                      'is_asthmatic', 'is_immunocompromised', 'is_elderly', 'is_child',
                      'is_trauma_patient')
        }),
        ('Interventions', {
            'fields': ('oxygen_given', 'oxygen_flow_rate', 'iv_line_placed', 'medications_given')
        }),
        ('Assessment', {
            'fields': ('priority', 'triage_score', 'colour_code', 'triage_notes', 
                      'special_instructions')
        }),
        ('Timestamps', {
            'fields': ('triage_start', 'triage_completed'),
            'classes': ('collapse',)
        })
    )
    
    def visit_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:visits_visit_change', args=[obj.visit.id])
        return format_html('<a href="{}">{}</a>', url, obj.visit.visit_number)
    visit_link.short_description = 'Visit'
    
    def patient_name(self, obj):
        return obj.visit.patient.full_name
    patient_name.admin_order_field = 'visit__patient__first_name'
    
    def priority_coloured(self, obj):
        colours = {
            'resuscitation': '#FF0000',
            'emergency': '#FF6600',
            'urgent': '#FFCC00',
            'less_urgent': '#00CC00',
            'non_urgent': '#0066CC'
        }
        colour = colours.get(obj.priority, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colour, obj.get_priority_display()
        )
    priority_coloured.short_description = 'Priority'
    
    def completed_status(self, obj):
        if obj.triage_completed:
            return format_html('<span style="color: green;">✓ Completed</span>')
        return format_html('<span style="color: orange;">⏳ In Progress</span>')
    completed_status.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not obj.triage_officer:
            obj.triage_officer = request.user
        obj.save()
    
    actions = ['export_selected']
    
    def export_selected(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="triage_records.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Visit Number', 'Patient Name', 'Priority', 'Triage Score',
            'Temperature', 'Heart Rate', 'BP', 'O2 Sat', 'Pain Score', 'Date'
        ])
        
        for triage in queryset:
            writer.writerow([
                triage.visit.visit_number,
                triage.visit.patient.full_name,
                triage.get_priority_display(),
                triage.triage_score,
                triage.temperature,
                triage.heart_rate,
                f"{triage.systolic_bp}/{triage.diastolic_bp}" if triage.systolic_bp else '',
                triage.oxygen_saturation,
                triage.pain_score,
                triage.triage_start.date()
            ])
        
        return response
    export_selected.short_description = "Export selected triage records to CSV"


@admin.register(TriageQueue)
class TriageQueueAdmin(admin.ModelAdmin):
    list_display = ['position', 'visit', 'patient_name', 'estimated_wait_time', 'called_at', 'completed_at']
    list_filter = ['completed_at']
    search_fields = ['visit__visit_number', 'visit__patient__first_name']
    raw_id_fields = ['visit', 'assigned_to']
    
    def patient_name(self, obj):
        return obj.visit.patient.full_name
    patient_name.short_description = 'Patient'