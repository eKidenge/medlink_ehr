from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Referral, ReferralNote


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        'referral_number', 'patient_link', 'referring_facility', 'receiving_facility',
        'priority_coloured', 'status_coloured', 'created_at'
    ]
    list_filter = ['status', 'priority', 'referral_type', 'created_at']
    search_fields = ['referral_number', 'patient__first_name', 'patient__last_name', 'receiving_facility']
    readonly_fields = ['referral_number', 'created_at', 'approved_at', 'completed_at', 'cancelled_at', 'qr_code_preview']
    raw_id_fields = ['patient', 'visit', 'referring_doctor', 'approved_by']
    
    fieldsets = (
        ('Referral Information', {
            'fields': ('referral_number', 'patient', 'visit', 'referral_type', 'priority')
        }),
        ('From', {
            'fields': ('referring_facility', 'referring_department', 'referring_doctor')
        }),
        ('To', {
            'fields': ('receiving_facility', 'receiving_department', 'receiving_doctor', 'receiving_contact')
        }),
        ('Clinical Information', {
            'fields': ('reason_for_referral', 'clinical_summary', 'provisional_diagnosis',
                      'investigations_done', 'treatment_given')
        }),
        ('Status', {
            'fields': ('status', 'feedback_from_receiving', 'outcome')
        }),
        ('Follow-up', {
            'fields': ('follow_up_required', 'follow_up_date'),
            'classes': ('collapse',)
        }),
        ('Secure Access', {
            'fields': ('qr_code_preview', 'access_token', 'token_expiry'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'approved_at', 'completed_at', 'cancelled_at'),
            'classes': ('collapse',)
        })
    )
    
    def patient_link(self, obj):
        url = reverse('admin:patients_patient_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)
    patient_link.short_description = 'Patient'
    
    def priority_coloured(self, obj):
        colours = {'emergency': '#F44336', 'urgent': '#FF9800', 'routine': '#4CAF50'}
        colour = colours.get(obj.priority, '#9E9E9E')
        return format_html('<span style="color: {};">{}</span>', colour, obj.get_priority_display())
    priority_coloured.short_description = 'Priority'
    
    def status_coloured(self, obj):
        colours = {
            'pending': '#FF9800', 'approved': '#2196F3', 'in_progress': '#9C27B0',
            'completed': '#4CAF50', 'rejected': '#F44336', 'cancelled': '#9E9E9E'
        }
        colour = colours.get(obj.status, '#9E9E9E')
        return format_html('<span style="color: {};">{}</span>', colour, obj.get_status_display())
    status_coloured.short_description = 'Status'
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="100" height="100" />', obj.qr_code.url)
        return 'Not generated'
    qr_code_preview.short_description = 'QR Code'
    
    actions = ['generate_qr_codes']
    
    def generate_qr_codes(self, request, queryset):
        from .views import ReferralViewSet
        view = ReferralViewSet()
        for referral in queryset:
            if not referral.qr_code:
                view._generate_qr_code(referral)
        self.message_user(request, f"Generated QR codes for {queryset.count()} referrals")
    generate_qr_codes.short_description = "Generate QR codes for selected referrals"


@admin.register(ReferralNote)
class ReferralNoteAdmin(admin.ModelAdmin):
    list_display = ['referral', 'author', 'note_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['referral__referral_number', 'note']
    raw_id_fields = ['referral', 'author']
    
    def note_preview(self, obj):
        return obj.note[:100] + '...' if len(obj.note) > 100 else obj.note
    note_preview.short_description = 'Note'