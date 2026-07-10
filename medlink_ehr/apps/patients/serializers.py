from rest_framework import serializers
from django.db import transaction
from .models import (
    Patient, PatientAllergy, PatientChronicDisease, 
    PatientVaccination, PatientMedicalHistory, PatientSurgicalHistory
)


class PatientAllergySerializer(serializers.ModelSerializer):
    confirmed_by_name = serializers.CharField(source='confirmed_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientAllergy
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class PatientChronicDiseaseSerializer(serializers.ModelSerializer):
    diagnosed_by_name = serializers.CharField(source='diagnosed_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientChronicDisease
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class PatientVaccinationSerializer(serializers.ModelSerializer):
    administered_by_name = serializers.CharField(source='administered_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientVaccination
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class PatientMedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientMedicalHistory
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class PatientSurgicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientSurgicalHistory
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    allergies = PatientAllergySerializer(many=True, read_only=True)
    chronic_diseases = PatientChronicDiseaseSerializer(many=True, read_only=True)
    vaccinations = PatientVaccinationSerializer(many=True, read_only=True)
    medical_history = PatientMedicalHistorySerializer(many=True, read_only=True)
    surgeries = PatientSurgicalHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ('id', 'patient_number', 'mrn_number', 'created_at', 'updated_at', 'qr_code_data')
    
    def validate(self, data):
        # Ensure at least one contact method
        if not data.get('phone_primary') and not data.get('email'):
            raise serializers.ValidationError("Either phone number or email is required")
        
        # Validate date of birth not in future
        if data.get('date_of_birth') and data['date_of_birth'] > timezone.now().date():
            raise serializers.ValidationError({"date_of_birth": "Date of birth cannot be in the future"})
        
        # Validate identification uniqueness
        id_type = data.get('id_type')
        id_number = data.get('identification_number')
        if id_type == 'national_id' and id_number:
            if Patient.objects.filter(identification_number=id_number).exclude(id=self.instance.id if self.instance else None).exists():
                raise serializers.ValidationError({"identification_number": "Patient with this National ID already exists"})
        
        return data


class PatientListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Patient
        fields = ['id', 'patient_number', 'mrn_number', 'full_name', 'first_name', 'last_name', 
                  'phone_primary', 'gender', 'age', 'is_active', 'created_at']


class PatientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new patients"""
    
    class Meta:
        model = Patient
        exclude = ['qr_code', 'qr_code_data', 'merged_to', 'is_merged']
        read_only_fields = ('id', 'patient_number', 'mrn_number', 'created_at', 'updated_at')
    
    @transaction.atomic
    def create(self, validated_data):
        patient = Patient.objects.create(**validated_data)
        return patient


class PatientMergeSerializer(serializers.Serializer):
    """Serializer for merging patients"""
    source_patient_id = serializers.IntegerField()
    target_patient_id = serializers.IntegerField()
    
    def validate(self, data):
        source = Patient.objects.filter(id=data['source_patient_id']).first()
        target = Patient.objects.filter(id=data['target_patient_id']).first()
        
        if not source or not target:
            raise serializers.ValidationError("Invalid patient IDs")
        
        if source.id == target.id:
            raise serializers.ValidationError("Cannot merge a patient with itself")
        
        if source.is_merged or target.is_merged:
            raise serializers.ValidationError("One or both patients are already merged")
        
        data['source'] = source
        data['target'] = target
        return data
    
    def save(self):
        source = self.validated_data['source']
        target = self.validated_data['target']
        source.merge_with(target)
        return target