from django.db import models
from django.utils import timezone
from apps.accounts.models import User


class ReportTemplate(models.Model):
    """Report template for generating custom reports"""
    
    REPORT_TYPES = (
        ('clinical', 'Clinical Report'),
        ('financial', 'Financial Report'),
        ('operational', 'Operational Report'),
        ('administrative', 'Administrative Report'),
        ('public_health', 'Public Health Report'),
    )
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    
    # Report configuration
    query_config = models.JSONField(default=dict, help_text="Report query configuration")
    columns = models.JSONField(default=list, help_text="Columns to display")
    filters = models.JSONField(default=dict, help_text="Available filters")
    
    # Output settings
    default_format = models.CharField(max_length=20, choices=(
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ), default='pdf')
    
    # Sharing
    is_public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(User, blank=True, related_name='shared_reports')
    
    # Schedule (for automated reports)
    is_scheduled = models.BooleanField(default=False)
    schedule_frequency = models.CharField(max_length=20, choices=(
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ), blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ReportJob(models.Model):
    """Scheduled report jobs"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='jobs')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_jobs')
    parameters = models.JSONField(default=dict)
    output_format = models.CharField(max_length=20)
    output_file = models.FileField(upload_to='reports/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report {self.template.name} - {self.created_at}"


class AuditReport(models.Model):
    """Audit log reports"""
    
    ACTION_TYPES = (
        ('access', 'Access Logs'),
        ('modification', 'Data Modifications'),
        ('export', 'Data Exports'),
        ('login', 'Login Attempts'),
        ('system', 'System Events'),
    )
    
    report_number = models.CharField(max_length=50, unique=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    
    # Results
    total_events = models.IntegerField(default=0)
    report_data = models.JSONField(default=dict)
    report_file = models.FileField(upload_to='audit_reports/', null=True, blank=True)
    
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def save(self, *args, **kwargs):
        if not self.report_number:
            self.report_number = f"AUD{timezone.now().strftime('%Y%m%d%H%M%S')}{User.objects.count()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.report_number} - {self.get_action_type_display()} ({self.date_from.date()} to {self.date_to.date()})"