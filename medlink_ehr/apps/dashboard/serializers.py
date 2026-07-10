"""
Serializers for dashboard app
"""
from rest_framework import serializers
from .models import DashboardWidget, UserDashboard, UserDashboardWidget, Notification
from apps.accounts.serializers import UserSerializer


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for DashboardWidget model"""
    
    widget_type_display = serializers.CharField(source='get_widget_type_display', read_only=True)
    
    class Meta:
        model = DashboardWidget
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class UserDashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for UserDashboardWidget model"""
    
    widget_details = DashboardWidgetSerializer(source='widget', read_only=True)
    
    class Meta:
        model = UserDashboardWidget
        fields = '__all__'
        read_only_fields = ('id',)


class UserDashboardSerializer(serializers.ModelSerializer):
    """Serializer for UserDashboard model"""
    
    user_details = UserSerializer(source='user', read_only=True)
    widgets = UserDashboardWidgetSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserDashboard
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'read_at')
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        diff = timezone.now() - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"