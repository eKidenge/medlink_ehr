"""
Serializers for visits app
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Visit, ClinicalNote, Vitals
from apps.patients.serializers import PatientListSerializer


class VitalsSerializer(serializers.ModelSerializer):
    """Serializer for Vitals model"""
    
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    blood_pressure_display = serializers.CharField(read_only=True)
    is_critical = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Vitals
        fields = '__all__'
        read_only_fields = ('id', 'bmi', 'recorded_at')


class ClinicalNoteSerializer(serializers.ModelSerializer):
    """Serializer for ClinicalNote model"""
    
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    note_type_display = serializers.CharField(source='get_note_type_display', read_only=True)
    
    class Meta:
        model = ClinicalNote
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class VisitListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone_primary', read_only=True)
    primary_doctor_name = serializers.CharField(source='primary_doctor.get_full_name', read_only=True)
    waiting_time = serializers.IntegerField(source='total_waiting_time', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Visit
        fields = [
            'id', 'visit_number', 'patient_name', 'patient_phone', 'visit_type',
            'status', 'status_display', 'priority', 'priority_display', 
            'primary_doctor_name', 'registration_time', 'check_in_time', 
            'consultation_start', 'waiting_time', 'payment_status'
        ]


class VisitSerializer(serializers.ModelSerializer):
    """Full Visit serializer"""
    
    patient_details = PatientListSerializer(source='patient', read_only=True)
    primary_doctor_name = serializers.CharField(source='primary_doctor.get_full_name', read_only=True)
    nurse_name = serializers.CharField(source='nurse.get_full_name', read_only=True)
    clinical_officer_name = serializers.CharField(source='clinical_officer.get_full_name', read_only=True)
    vitals = VitalsSerializer(read_only=True)
    clinical_notes_detail = ClinicalNoteSerializer(many=True, read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    visit_type_display = serializers.CharField(source='get_visit_type_display', read_only=True)
    
    class Meta:
        model = Visit
        fields = '__all__'
        read_only_fields = (
            'id', 'visit_number', 'registration_time', 'updated_at', 
            'duration_minutes', 'total_waiting_time'
        )


class VisitCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new visits"""
    
    class Meta:
        model = Visit
        fields = [
            'patient', 'visit_type', 'priority', 'chief_complaint', 
            'history_of_present_illness', 'primary_doctor', 'referred_from'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['status'] = 'registered'
        return super().create(validated_data)


class VisitUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating visit status and clinical info"""
    
    class Meta:
        model = Visit
        fields = [
            'status', 'priority', 'primary_doctor', 'clinical_officer', 'nurse',
            'provisional_diagnosis', 'final_diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'follow_up_doctor',
            'discharge_instructions', 'outcome'
        ]
    
    def update(self, instance, validated_data):
        # Handle status transitions
        new_status = validated_data.get('status')
        
        if new_status == 'check_in' and not instance.check_in_time:
            validated_data['check_in_time'] = timezone.now()
        elif new_status == 'triage' and not instance.triage_time:
            validated_data['triage_time'] = timezone.now()
        elif new_status == 'consultation' and not instance.consultation_start:
            validated_data['consultation_start'] = timezone.now()
        elif new_status in ['completed', 'discharged'] and not instance.completion_time:
            validated_data['completion_time'] = timezone.now()
        
        return super().update(instance, validated_data)


class VisitCheckInSerializer(serializers.Serializer):
    """Serializer for patient check-in"""
    
    visit_id = serializers.IntegerField(required=False)
    patient_id = serializers.IntegerField(required=False)
    visit_type = serializers.CharField(default='outpatient')
    chief_complaint = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if not data.get('visit_id') and not data.get('patient_id'):
            raise serializers.ValidationError("Either visit_id or patient_id is required")
        return data