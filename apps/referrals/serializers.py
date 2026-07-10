"""
Serializers for referrals app
"""
from rest_framework import serializers
from .models import Referral, ReferralNote
from apps.patients.serializers import PatientListSerializer


class ReferralNoteSerializer(serializers.ModelSerializer):
    """Referral note serializer"""
    
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    
    class Meta:
        model = ReferralNote
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class ReferralListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    referring_doctor_name = serializers.CharField(source='referring_doctor.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    referral_type_display = serializers.CharField(source='get_referral_type_display', read_only=True)
    
    class Meta:
        model = Referral
        fields = [
            'id', 'referral_number', 'patient_name', 'referring_facility',
            'receiving_facility', 'referring_doctor_name', 'status',
            'status_display', 'priority', 'priority_display', 'referral_type',
            'referral_type_display', 'created_at', 'completed_at'
        ]


class ReferralSerializer(serializers.ModelSerializer):
    """Full referral serializer"""
    
    patient_details = PatientListSerializer(source='patient', read_only=True)
    referring_doctor_name = serializers.CharField(source='referring_doctor.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    referral_type_display = serializers.CharField(source='get_referral_type_display', read_only=True)
    notes = ReferralNoteSerializer(many=True, read_only=True)
    
    class Meta:
        model = Referral
        fields = '__all__'
        read_only_fields = (
            'id', 'referral_number', 'created_at', 'approved_at', 
            'completed_at', 'cancelled_at', 'access_token', 'token_expiry'
        )


class ReferralCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating referrals"""
    
    class Meta:
        model = Referral
        fields = [
            'patient', 'visit', 'referral_type', 'priority', 'receiving_facility',
            'receiving_department', 'receiving_doctor', 'receiving_contact',
            'reason_for_referral', 'clinical_summary', 'provisional_diagnosis',
            'investigations_done', 'treatment_given', 'follow_up_required',
            'follow_up_date'
        ]
    
    def create(self, validated_data):
        validated_data['referring_facility'] = self.context['request'].user.department.name if self.context['request'].user.department else 'Unknown'
        validated_data['referring_doctor'] = self.context['request'].user
        return super().create(validated_data)


class ReferralStatusSerializer(serializers.Serializer):
    """Serializer for updating referral status"""
    
    status = serializers.ChoiceField(choices=Referral.STATUS_CHOICES)
    feedback = serializers.CharField(required=False, allow_blank=True)
    outcome = serializers.CharField(required=False, allow_blank=True)