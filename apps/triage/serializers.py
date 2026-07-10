from rest_framework import serializers
from .models import Triage, TriageQueue
from apps.visits.serializers import VisitListSerializer


class TriageListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    
    visit_number = serializers.CharField(source='visit.visit_number', read_only=True)
    patient_name = serializers.CharField(source='visit.patient.full_name', read_only=True)
    patient_age = serializers.IntegerField(source='visit.patient.age', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    colour_code = serializers.CharField(read_only=True)
    
    class Meta:
        model = Triage
        fields = [
            'id', 'visit_number', 'patient_name', 'patient_age', 'priority',
            'priority_display', 'colour_code', 'triage_score', 'triage_start',
            'triage_completed', 'avpu_score'
        ]


class TriageSerializer(serializers.ModelSerializer):
    """Full triage serializer"""
    
    visit_details = VisitListSerializer(source='visit', read_only=True)
    triage_officer_name = serializers.CharField(source='triage_officer.get_full_name', read_only=True)
    completed_by_name = serializers.CharField(source='completed_by.get_full_name', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    avpu_display = serializers.CharField(source='get_avpu_score_display', read_only=True)
    
    class Meta:
        model = Triage
        fields = '__all__'
        read_only_fields = (
            'id', 'triage_score', 'colour_code', 'triage_start', 'triage_completed'
        )


class TriageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating triage record"""
    
    class Meta:
        model = Triage
        fields = [
            'visit', 'temperature', 'heart_rate', 'respiratory_rate',
            'systolic_bp', 'diastolic_bp', 'oxygen_saturation', 'blood_glucose',
            'avpu_score', 'pain_score', 'chief_complaint', 'mechanism_of_injury'
        ]
    
    def validate(self, data):
        visit = data.get('visit')
        
        # Check if visit is eligible for triage
        if visit.status not in ['check_in', 'registered']:
            raise serializers.ValidationError(
                {"visit": "Visit must be checked in before triage"}
            )
        
        # Validate vital signs ranges
        if data.get('temperature'):
            temp = data['temperature']
            if temp < 30 or temp > 43:
                raise serializers.ValidationError(
                    {"temperature": "Temperature out of normal range (30-43°C)"}
                )
        
        if data.get('heart_rate'):
            hr = data['heart_rate']
            if hr < 30 or hr > 200:
                raise serializers.ValidationError(
                    {"heart_rate": "Heart rate out of normal range (30-200 bpm)"}
                )
        
        return data


class TriageCompleteSerializer(serializers.ModelSerializer):
    """Serializer for completing triage"""
    
    class Meta:
        model = Triage
        fields = [
            'temperature', 'heart_rate', 'respiratory_rate', 'systolic_bp',
            'diastolic_bp', 'oxygen_saturation', 'blood_glucose', 'avpu_score',
            'glasgow_coma_score', 'pain_score', 'pain_location', 'breathing_difficulty',
            'use_accessory_muscles', 'capillary_refill', 'peripheral_pulses',
            'skin_turgor', 'rash', 'rash_description', 'bruises', 'swelling',
            'swelling_location', 'is_pregnant', 'pregnancy_weeks', 'is_diabetic',
            'is_hypertensive', 'is_asthmatic', 'is_immunocompromised', 'is_elderly',
            'is_child', 'is_trauma_patient', 'oxygen_given', 'oxygen_flow_rate',
            'iv_line_placed', 'medications_given', 'triage_notes', 'special_instructions'
        ]


class TriageQueueSerializer(serializers.ModelSerializer):
    """Triage queue serializer"""
    
    patient_name = serializers.CharField(source='visit.patient.full_name', read_only=True)
    visit_number = serializers.CharField(source='visit.visit_number', read_only=True)
    priority = serializers.CharField(source='visit.priority', read_only=True)
    
    class Meta:
        model = TriageQueue
        fields = '__all__'
        read_only_fields = ('id', 'position')