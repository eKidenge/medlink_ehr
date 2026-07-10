"""
Signals for the reports app - Handles report generation events
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ReportJob, AuditReport
from apps.dashboard.models import Notification


@receiver(post_save, sender=ReportJob)
def report_job_post_save(sender, instance, created, **kwargs):
    """
    Handle report job status changes
    """
    if not created and hasattr(instance, '_status_changed'):
        old_status, new_status = instance._status_changed
        
        if new_status == 'completed':
            # Notify user that report is ready
            Notification.objects.create(
                recipient=instance.requested_by,
                title='Report Ready',
                message=f'Your report "{instance.template.name}" has been generated and is ready for download.',
                notification_type='success',
                action_url=f'/reports/jobs/{instance.id}/download/'
            )
        
        elif new_status == 'failed':
            # Notify user about failure
            Notification.objects.create(
                recipient=instance.requested_by,
                title='Report Generation Failed',
                message=f'Your report "{instance.template.name}" failed to generate. Error: {instance.error_message[:200] if instance.error_message else "Unknown error"}',
                notification_type='error',
                action_url=f'/reports/'
            )
        
        # Log status change
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='update',
            model_name='ReportJob',
            object_id=str(instance.id),
            object_repr=f"Report {instance.template.name}",
            changes={'status': f'{old_status} -> {new_status}'},
            ip_address='',
            user_agent=''
        )


@receiver(post_save, sender=AuditReport)
def audit_report_post_save(sender, instance, created, **kwargs):
    """
    Handle audit report creation
    """
    if created:
        # Notify admin
        from apps.accounts.models import User
        admins = User.objects.filter(role__in=['admin', 'super_admin'])
        
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title='Audit Report Generated',
                message=f'A new audit report has been generated. Type: {instance.get_action_type_display()}. Period: {instance.date_from.date()} to {instance.date_to.date()}',
                notification_type='info',
                action_url=f'/admin/reports/auditreport/{instance.id}/change/'
            )
        
        # Log creation
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='AuditReport',
            object_id=str(instance.id),
            object_repr=instance.report_number,
            changes={
                'action_type': instance.action_type,
                'date_range': f"{instance.date_from} to {instance.date_to}",
                'total_events': instance.total_events
            },
            ip_address='',
            user_agent=''
        )