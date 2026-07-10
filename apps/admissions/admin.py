from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Ward, Bed, Admission, DailyRound


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'ward_type', 'total_beds', 'occupied_beds', 'available_beds', 'occupancy_rate', 'is_active']
    list_filter = ['ward_type', 'is_active', 'floor']
    search_fields = ['name', 'code']
    readonly_fields = ['occupied_beds', 'available_beds']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'ward_type', 'floor', 'building')
        }),
        ('Capacity', {
            'fields': ('total_beds', 'occupied_beds', 'available_beds')
        }),
        ('Staff', {
            'fields': ('ward_manager', 'in_charge_nurse')
        }),
        ('Facilities', {
            'fields': ('has_oxygen', 'has_suction', 'has_monitoring', 'has_private_bathroom')
        }),
        ('Financial', {
            'fields': ('daily_rate',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_under_maintenance')
        })
    )
    
    def occupancy_rate(self, obj):
        if obj.total_beds > 0:
            rate = (obj.occupied_beds / obj.total_beds) * 100
            colour = 'red' if rate > 90 else 'orange' if rate > 70 else 'green'
            return format_html('<span style="color: {};">{}%</span>', colour, round(rate, 1))
        return '0%'
    occupancy_rate.short_description = 'Occupancy'
    
    actions = ['update_bed_counts']
    
    def update_bed_counts(self, request, queryset):
        for ward in queryset:
            ward.update_bed_counts()
        self.message_user(request, f"Updated bed counts for {queryset.count()} wards")
    update_bed_counts.short_description = "Update bed counts for selected wards"


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ['bed_number', 'ward_link', 'bed_type', 'is_occupied', 'is_available', 'current_patient_link']
    list_filter = ['ward', 'bed_type', 'is_occupied', 'is_available']
    search_fields = ['bed_number', 'ward__name']
    raw_id_fields = ['current_patient', 'current_admission']
    
    def ward_link(self, obj):
        url = reverse('admin:admissions_ward_change', args=[obj.ward.id])
        return format_html('<a href="{}">{}</a>', url, obj.ward.name)
    ward_link.short_description = 'Ward'
    
    def current_patient_link(self, obj):
        if obj.current_patient:
            url = reverse('admin:patients_patient_change', args=[obj.current_patient.id])
            return format_html('<a href="{}">{}</a>', url, obj.current_patient.full_name)
        return '-'
    current_patient_link.short_description = 'Current Patient'


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = [
        'admission_number', 'patient_link', 'ward_link', 'bed_number', 
        'admission_date', 'status_coloured', 'length_of_stay'
    ]
    list_filter = ['status', 'admission_type', 'admission_date', 'ward']
    search_fields = ['admission_number', 'patient__first_name', 'patient__last_name']
    readonly_fields = ['admission_number', 'admission_date', 'length_of_stay_days']
    raw_id_fields = ['patient', 'visit', 'ward', 'bed', 'admitting_doctor', 'discharged_by']
    
    fieldsets = (
        ('Admission Information', {
            'fields': ('admission_number', 'patient', 'visit', 'admission_type', 'admission_date')
        }),
        ('Ward & Bed', {
            'fields': ('ward', 'bed')
        }),
        ('Clinical Information', {
            'fields': ('admitting_doctor', 'primary_diagnosis', 'secondary_diagnosis', 
                      'admitting_notes', 'condition_on_admission')
        }),
        ('Status', {
            'fields': ('status', 'expected_discharge_date')
        }),
        ('Discharge Information', {
            'fields': ('discharge_date', 'discharge_status', 'discharge_summary', 
                      'discharge_instructions', 'discharged_by'),
            'classes': ('collapse',)
        }),
        ('Financial', {
            'fields': ('deposit_amount', 'total_charges'),
            'classes': ('collapse',)
        }),
        ('Transfer', {
            'fields': ('transferred_from', 'transferred_to', 'transfer_reason'),
            'classes': ('collapse',)
        })
    )
    
    def patient_link(self, obj):
        url = reverse('admin:patients_patient_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)
    patient_link.short_description = 'Patient'
    
    def ward_link(self, obj):
        url = reverse('admin:admissions_ward_change', args=[obj.ward.id])
        return format_html('<a href="{}">{}</a>', url, obj.ward.name)
    ward_link.short_description = 'Ward'
    
    def bed_number(self, obj):
        return obj.bed.bed_number if obj.bed else '-'
    bed_number.short_description = 'Bed'
    
    def status_coloured(self, obj):
        colours = {
            'admitted': '#2196F3',
            'in_treatment': '#FF9800',
            'stable': '#4CAF50',
            'critical': '#F44336',
            'discharged': '#9E9E9E',
            'transferred': '#9C27B0',
            'expired': '#000000',
            'absconded': '#795548'
        }
        colour = colours.get(obj.status, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colour, obj.get_status_display()
        )
    status_coloured.short_description = 'Status'
    
    def length_of_stay(self, obj):
        return f"{obj.length_of_stay_days} days"
    length_of_stay.short_description = 'LOS'
    
    actions = ['discharge_selected']
    
    def discharge_selected(self, request, queryset):
        for admission in queryset.filter(status__in=['admitted', 'in_treatment', 'stable', 'critical']):
            admission.discharge('home', 'Discharged by admin', request.user)
        self.message_user(request, f"Discharged {queryset.count()} patients")
    discharge_selected.short_description = "Discharge selected patients"


@admin.register(DailyRound)
class DailyRoundAdmin(admin.ModelAdmin):
    list_display = ['admission', 'doctor', 'round_date', 'temperature', 'blood_pressure']
    list_filter = ['round_date']
    search_fields = ['admission__patient__first_name', 'admission__patient__last_name', 'doctor__username']
    raw_id_fields = ['admission', 'doctor']