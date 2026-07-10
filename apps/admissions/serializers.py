"""
Serializers for admissions app
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Ward, Bed, Admission, DailyRound
from apps.patients.serializers import PatientListSerializer


class WardSerializer(serializers.ModelSerializer):
    """Ward serializer"""
    
    occupancy_rate = serializers.SerializerMethodField()
    ward_type_display = serializers.CharField(source='get_ward_type_display', read_only=True)
    
    class Meta:
        model = Ward
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'occupied_beds')
    
    def get_occupancy_rate(self, obj):
        if obj.total_beds > 0:
            return round((obj.occupied_beds / obj.total_beds) * 100, 1)
        return 0


class BedSerializer(serializers.ModelSerializer):
    """Bed serializer"""
    
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    bed_type_display = serializers.CharField(source='get_bed_type_display', read_only=True)
    current_patient_name = serializers.CharField(source='current_patient.full_name', read_only=True)
    
    class Meta:
        model = Bed
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class DailyRoundSerializer(serializers.ModelSerializer):
    """Daily round serializer"""
    
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    admission_number = serializers.CharField(source='admission.admission_number', read_only=True)
    patient_name = serializers.CharField(source='admission.patient.full_name', read_only=True)
    
    class Meta:
        model = DailyRound
        fields = '__all__'
        read_only_fields = ('id', 'round_date')


class AdmissionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone_primary', read_only=True)
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    bed_number = serializers.CharField(source='bed.bed_number', read_only=True)
    doctor_name = serializers.CharField(source='admitting_doctor.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    admission_type_display = serializers.CharField(source='get_admission_type_display', read_only=True)
    length_of_stay = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Admission
        fields = [
            'id', 'admission_number', 'patient_name', 'patient_phone', 'ward_name',
            'bed_number', 'doctor_name', 'primary_diagnosis', 'status', 'status_display',
            'admission_date', 'length_of_stay', 'admission_type', 'admission_type_display'
        ]


class AdmissionSerializer(serializers.ModelSerializer):
    """Full admission serializer"""
    
    patient_details = PatientListSerializer(source='patient', read_only=True)
    ward_details = WardSerializer(source='ward', read_only=True)
    bed_details = BedSerializer(source='bed', read_only=True)
    admitting_doctor_name = serializers.CharField(source='admitting_doctor.get_full_name', read_only=True)
    discharged_by_name = serializers.CharField(source='discharged_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    admission_type_display = serializers.CharField(source='get_admission_type_display', read_only=True)
    length_of_stay_days = serializers.IntegerField(source='length_of_stay_days', read_only=True)
    rounds = DailyRoundSerializer(many=True, read_only=True)
    
    class Meta:
        model = Admission
        fields = '__all__'
        read_only_fields = (
            'id', 'admission_number', 'admission_date', 'updated_at',
            'length_of_stay_days', 'total_charges'
        )


class AdmissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating admissions"""
    
    class Meta:
        model = Admission
        fields = [
            'patient', 'visit', 'admission_type', 'ward', 'bed',
            'admitting_doctor', 'primary_diagnosis', 'secondary_diagnosis',
            'admitting_notes', 'condition_on_admission', 'deposit_amount'
        ]
    
    def validate(self, data):
        # Check if bed is available
        bed = data.get('bed')
        if bed and bed.is_occupied:
            raise serializers.ValidationError({"bed": "This bed is already occupied"})
        
        # Check if patient already has active admission
        patient = data.get('patient')
        if Admission.objects.filter(patient=patient, status__in=['admitted', 'in_treatment', 'stable', 'critical']).exists():
            raise serializers.ValidationError(
                {"patient": "Patient already has an active admission"}
            )
        
        return data
    
    def create(self, validated_data):
        bed = validated_data.get('bed')
        admission = super().create(validated_data)
        
        # Occupy the bed
        if bed:
            bed.occupy(admission)
        
        # Update visit
        visit = admission.visit
        visit.requires_admission = True
        visit.status = 'admitted'
        visit.save()
        
        return admission


class DischargeSerializer(serializers.Serializer):
    """Serializer for discharging patients"""
    
    discharge_status = serializers.ChoiceField(choices=Admission.DISCHARGE_STATUS)
    discharge_summary = serializers.CharField(required=True)
    
    def validate_discharge_summary(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Discharge summary must be at least 10 characters")
        return value