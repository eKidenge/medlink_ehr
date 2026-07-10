"""
Serializers for pharmacy app
"""
from rest_framework import serializers
from .models import Medication, Prescription, StockTransaction
from apps.patients.serializers import PatientListSerializer


class MedicationSerializer(serializers.ModelSerializer):
    """Medication serializer"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    drug_form_display = serializers.CharField(source='get_drug_form_display', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Medication
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_is_low_stock(self, obj):
        return obj.is_low_stock()


class PrescriptionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    medication_name = serializers.CharField(source='medication.generic_name', read_only=True)
    doctor_name = serializers.CharField(source='prescribing_doctor.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    route_display = serializers.CharField(source='get_route_display', read_only=True)
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'prescription_number', 'patient_name', 'medication_name', 
            'dosage', 'quantity', 'dispensed_quantity', 'status', 'status_display',
            'route', 'route_display', 'prescribed_at', 'dispensed_at'
        ]


class PrescriptionSerializer(serializers.ModelSerializer):
    """Full prescription serializer"""
    
    patient_details = PatientListSerializer(source='patient', read_only=True)
    medication_details = MedicationSerializer(source='medication', read_only=True)
    prescribing_doctor_name = serializers.CharField(source='prescribing_doctor.get_full_name', read_only=True)
    dispensed_by_name = serializers.CharField(source='dispensed_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    route_display = serializers.CharField(source='get_route_display', read_only=True)
    
    class Meta:
        model = Prescription
        fields = '__all__'
        read_only_fields = ('id', 'prescription_number', 'prescribed_at', 'refills_remaining')


class PrescriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating prescriptions"""
    
    class Meta:
        model = Prescription
        fields = [
            'patient', 'visit', 'medication', 'dosage', 'frequency',
            'duration', 'quantity', 'route', 'special_instructions',
            'food_instructions', 'refills_allowed', 'clinical_notes'
        ]
    
    def validate(self, data):
        # Check if medication is active
        if not data['medication'].is_active:
            raise serializers.ValidationError({"medication": "This medication is not active"})
        
        # Check if prescription requires prescription (controlled substances)
        if data['medication'].requires_prescription:
            if self.context['request'].user.role not in ['doctor', 'clinical_officer']:
                raise serializers.ValidationError(
                    {"medication": "Only doctors can prescribe this medication"}
                )
        
        return data
    
    def create(self, validated_data):
        validated_data['prescribing_doctor'] = self.context['request'].user
        return super().create(validated_data)


class DispenseSerializer(serializers.Serializer):
    """Serializer for dispensing medication"""
    
    quantity = serializers.IntegerField(min_value=1)
    
    def validate_quantity(self, value):
        prescription = self.context['prescription']
        remaining = prescription.quantity - prescription.dispensed_quantity
        
        if value > remaining:
            raise serializers.ValidationError(f"Cannot dispense more than remaining quantity ({remaining})")
        
        return value


class StockTransactionSerializer(serializers.ModelSerializer):
    """Stock transaction serializer"""
    
    medication_name = serializers.CharField(source='medication.generic_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = StockTransaction
        fields = '__all__'
        read_only_fields = ('id', 'created_at')