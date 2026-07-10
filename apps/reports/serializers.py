"""
Serializers for reports app
"""
from rest_framework import serializers
from .models import ReportTemplate, ReportJob, AuditReport
from apps.accounts.serializers import UserSerializer


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ReportTemplate model"""
    
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ReportTemplate
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by')


class ReportJobSerializer(serializers.ModelSerializer):
    """Serializer for ReportJob model"""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ReportJob
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'completed_at')


class AuditReportSerializer(serializers.ModelSerializer):
    """Serializer for AuditReport model"""
    
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = AuditReport
        fields = '__all__'
        read_only_fields = ('id', 'report_number', 'generated_at')