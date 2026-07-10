"""
Serializers for laboratory app
"""
from rest_framework import serializers
from .models import LabTestCategory, LabTest, LabRequest, LabResult
from apps.patients.serializers import PatientListSerializer
from apps.visits.serializers import VisitListSerializer


class LabTestCategorySerializer(serializers.ModelSerializer):
    """Lab test category serializer"""
    
    test_count = serializers.IntegerField(source='tests.count', read_only=True)
    
    class Meta:
        model = LabTestCategory
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class LabTestSerializer(serializers.ModelSerializer):
    """Lab test serializer"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    specimen_type_display = serializers.CharField(source='get_specimen_type_display', read_only=True)
    
    class Meta:
        model = LabTest
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class LabResultSerializer(serializers.ModelSerializer):
    """Lab result serializer"""
    
    class Meta:
        model = LabResult
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class LabRequestListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    test_name = serializers.CharField(source='test.name', read_only=True)
    requesting_doctor_name = serializers.CharField(source='requesting_doctor.get_full_name', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = LabRequest
        fields = [
            'id', 'request_number', 'patient_name', 'test_name', 'priority',
            'priority_display', 'status', 'status_display', 'requesting_doctor_name',
            'created_at', 'completed_at', 'is_abnormal'
        ]


class LabRequestSerializer(serializers.ModelSerializer):
    """Full lab request serializer"""
    
    patient_details = PatientListSerializer(source='patient', read_only=True)
    visit_details = VisitListSerializer(source='visit', read_only=True)
    test_details = LabTestSerializer(source='test', read_only=True)
    requesting_doctor_name = serializers.CharField(source='requesting_doctor.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    rejected_by_name = serializers.CharField(source='rejected_by.get_full_name', read_only=True)
    specimen_collected_by_name = serializers.CharField(source='specimen_collected_by.get_full_name', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    detailed_results = LabResultSerializer(many=True, read_only=True)
    
    class Meta:
        model = LabRequest
        fields = '__all__'
        read_only_fields = (
            'id', 'request_number', 'created_at', 'updated_at',
            'specimen_collected_at', 'started_processing_at', 'completed_at',
            'verified_at'
        )


class LabRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating lab requests"""
    
    class Meta:
        model = LabRequest
        fields = [
            'patient', 'visit', 'test', 'priority', 'clinical_notes', 'diagnosis'
        ]
    
    def validate(self, data):
        # Check if there's already a pending request for same test
        existing = LabRequest.objects.filter(
            patient=data['patient'],
            test=data['test'],
            status__in=['pending', 'collected', 'processing']
        ).exists()
        
        if existing:
            raise serializers.ValidationError(
                {"test": "There's already a pending request for this test"}
            )
        
        return data
    
    def create(self, validated_data):
        validated_data['requesting_doctor'] = self.context['request'].user
        return super().create(validated_data)