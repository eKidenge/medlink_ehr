from django.db import models
from django.utils import timezone
from apps.accounts.models import User


class DashboardWidget(models.Model):
    """Dashboard widget configuration"""
    
    WIDGET_TYPES = (
        ('counter', 'Counter'),
        ('chart', 'Chart'),
        ('table', 'Table'),
        ('list', 'List'),
        ('calendar', 'Calendar'),
        ('alert', 'Alert'),
    )
    
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    
    # Configuration
    config = models.JSONField(default=dict, help_text="Widget-specific configuration")
    query_config = models.JSONField(default=dict, help_text="Data query configuration")
    
    # Dimensions
    width = models.IntegerField(default=4, help_text="Grid width (1-12)")
    height = models.IntegerField(default=3, help_text="Grid height")
    
    # Position
    order = models.IntegerField(default=0)
    
    # Visibility
    is_visible = models.BooleanField(default=True)
    visible_to_roles = models.JSONField(default=list, help_text="List of roles that can see this widget")
    
    # Refresh
    auto_refresh = models.BooleanField(default=False)
    refresh_interval = models.IntegerField(default=60, help_text="Refresh interval in seconds")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.name


class UserDashboard(models.Model):
    """User-specific dashboard configuration"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard')
    widgets = models.ManyToManyField(DashboardWidget, through='UserDashboardWidget')
    layout = models.JSONField(default=dict, help_text="Dashboard layout configuration")
    theme = models.CharField(max_length=50, default='light')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()}'s Dashboard"


class UserDashboardWidget(models.Model):
    """User-specific widget settings"""
    
    user_dashboard = models.ForeignKey(UserDashboard, on_delete=models.CASCADE)
    widget = models.ForeignKey(DashboardWidget, on_delete=models.CASCADE)
    
    # Position override
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    order = models.IntegerField(default=0)
    
    # Settings override
    settings = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['order']
        unique_together = ['user_dashboard', 'widget']
    
    def __str__(self):
        return f"{self.user_dashboard.user.username} - {self.widget.name}"


class Notification(models.Model):
    """System notifications"""
    
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('alert', 'Alert'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    
    # Action link
    action_url = models.CharField(max_length=500, blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Priority
    is_urgent = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()