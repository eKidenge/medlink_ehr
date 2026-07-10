from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from .models import (
    Patient, PatientAllergy, PatientChronicDisease,
    PatientVaccination, PatientMedicalHistory, PatientSurgicalHistory
)


class PatientAllergyInline(admin.TabularInline):
    model = PatientAllergy
    extra = 1
    fields = ['allergen', 'severity', 'reaction', 'onset_date']


class PatientChronicDiseaseInline(admin.TabularInline):
    model = PatientChronicDisease
    extra = 1
    fields = ['disease_name', 'diagnosed_date', 'status']


class PatientVaccinationInline(admin.TabularInline):
    model = PatientVaccination
    extra = 1
    fields = ['vaccine_name', 'dose_number', 'date_administered', 'next_due_date']


class PatientMedicalHistoryInline(admin.TabularInline):
    model = PatientMedicalHistory
    extra = 1
    fields = ['condition', 'diagnosed_date', 'resolved_date']


@admin.register(Patient)
class PatientAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ['patient_number', 'full_name', 'phone_primary', 'gender', 'age', 'created_at', 'view_qr']
    list_filter = ['gender', 'is_active', 'has_allergies', 'has_chronic_diseases', 'county', 'created_at']
    search_fields = ['patient_number', 'mrn_number', 'first_name', 'last_name', 'phone_primary', 'identification_number', 'nhif_number']
    readonly_fields = ['patient_number', 'mrn_number', 'age', 'created_at', 'updated_at', 'qr_code_preview']
    inlines = [PatientAllergyInline, PatientChronicDiseaseInline, PatientVaccinationInline, PatientMedicalHistoryInline]
    
    fieldsets = (
        ('Primary Information', {
            'fields': ('patient_number', 'mrn_number', 'qr_code_preview', 'first_name', 'middle_name', 'last_name', 'maiden_name')
        }),
        ('Identification', {
            'fields': ('id_type', 'identification_number', 'passport_number', 'birth_certificate_number', 'nhif_number')
        }),
        ('Contact Information', {
            'fields': ('phone_primary', 'phone_secondary', 'email', 'alternative_email')
        }),
        ('Demographics', {
            'fields': ('date_of_birth', 'age', 'gender', 'marital_status', 'blood_type')
        }),
        ('Address', {
            'fields': ('county', 'sub_county', 'ward', 'village', 'location', 'sub_location', 'physical_address', 'landmark')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone')
        }),
        ('Employment & Insurance', {
            'fields': ('occupation', 'employer', 'insurance_provider', 'insurance_number', 'insurance_valid_until')
        }),
        ('Medical Flags', {
            'fields': ('has_allergies', 'has_chronic_diseases', 'is_pregnant', 'expected_delivery_date', 'is_disabled', 'disability_type')
        }),
        ('Status', {
            'fields': ('is_active', 'is_deceased', 'date_of_death', 'cause_of_death')
        }),
        ('System Fields', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        return obj.full_name
    full_name.admin_order_field = 'first_name'
    
    def view_qr(self, obj):
        if obj.qr_code:
            return format_html('<a href="{}" target="_blank">View QR</a>', obj.qr_code.url)
        return "Not generated"
    view_qr.short_description = 'QR Code'
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="150" height="150" />', obj.qr_code.url)
        return "No QR code generated"
    qr_code_preview.short_description = 'QR Code Preview'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        obj.save()
    
    actions = ['generate_qr_codes', 'export_selected']
    
    def generate_qr_codes(self, request, queryset):
        for patient in queryset:
            patient.generate_qr_code()
        self.message_user(request, f"Generated QR codes for {queryset.count()} patients")
    generate_qr_codes.short_description = "Generate QR codes for selected patients"
    
    def export_selected(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="patients.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Patient Number', 'Name', 'Phone', 'Email', 'Gender', 'Age', 'County', 'Created At'])
        
        for patient in queryset:
            writer.writerow([
                patient.patient_number, patient.full_name, patient.phone_primary,
                patient.email, patient.get_gender_display(), patient.age,
                patient.county, patient.created_at
            ])
        
        return response
    export_selected.short_description = "Export selected patients to CSV"


@admin.register(PatientAllergy)
class PatientAllergyAdmin(admin.ModelAdmin):
    list_display = ['patient', 'allergen', 'severity', 'reaction', 'created_at']
    list_filter = ['severity', 'allergen_type', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'allergen']
    raw_id_fields = ['patient', 'confirmed_by']


@admin.register(PatientChronicDisease)
class PatientChronicDiseaseAdmin(admin.ModelAdmin):
    list_display = ['patient', 'disease_name', 'diagnosed_date', 'status']
    list_filter = ['status', 'diagnosed_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'disease_name', 'icd10_code']
    raw_id_fields = ['patient', 'diagnosed_by']


@admin.register(PatientVaccination)
class PatientVaccinationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'vaccine_name', 'dose_number', 'date_administered', 'next_due_date']
    list_filter = ['vaccine_name', 'date_administered']
    search_fields = ['patient__first_name', 'patient__last_name', 'vaccine_name']
    raw_id_fields = ['patient', 'administered_by']


@admin.register(PatientMedicalHistory)
class PatientMedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ['patient', 'condition', 'diagnosed_date']
    list_filter = ['diagnosed_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'condition']
    raw_id_fields = ['patient']


@admin.register(PatientSurgicalHistory)
class PatientSurgicalHistoryAdmin(admin.ModelAdmin):
    list_display = ['patient', 'procedure_name', 'surgery_date', 'hospital']
    list_filter = ['surgery_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'procedure_name']
    raw_id_fields = ['patient']