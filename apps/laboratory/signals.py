"""
Signals for the laboratory app - Handles test requests and results
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import LabRequest, LabResult
from apps.dashboard.models import Notification
from apps.accounts.models import User


@receiver(post_save, sender=LabRequest)
def lab_request_post_save(sender, instance, created, **kwargs):
    """
    Handle lab request creation and status changes
    """
    if created:
        # Notify lab staff about new request
        notify_lab_staff(instance, 'new')
        
        # Notify requesting doctor that request was submitted
        Notification.objects.create(
            recipient=instance.requesting_doctor,
            title='Lab Request Submitted',
            message=f'Lab request #{instance.request_number} for {instance.test.name} has been submitted for patient {instance.patient.full_name}.',
            notification_type='info',
            action_url=f'/laboratory/detail/{instance.id}/'
        )
        
        # Log creation
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='LabRequest',
            object_id=str(instance.id),
            object_repr=instance.request_number,
            changes={
                'patient': instance.patient.full_name,
                'test': instance.test.name,
                'priority': instance.priority
            },
            ip_address='',
            user_agent=''
        )
    
    # Check for status changes
    if hasattr(instance, '_status_changed'):
        old_status, new_status = instance._status_changed
        
        if new_status == 'collected':
            # Notify lab tech that specimen is ready
            if instance.assigned_to:
                Notification.objects.create(
                    recipient=instance.assigned_to,
                    title='Specimen Ready for Processing',
                    message=f'Specimen for test #{instance.request_number} ({instance.test.name}) has been collected and is ready for processing.',
                    notification_type='info',
                    action_url=f'/laboratory/processing/'
                )
        
        elif new_status == 'completed':
            # Notify requesting doctor that results are ready
            Notification.objects.create(
                recipient=instance.requesting_doctor,
                title='Lab Results Ready',
                message=f'Results for test #{instance.request_number} ({instance.test.name}) are now available for patient {instance.patient.full_name}.',
                notification_type='success',
                action_url=f'/laboratory/detail/{instance.id}/',
                is_urgent=(instance.priority == 'stat')
            )
            
            # Also notify for abnormal results
            if instance.is_abnormal:
                Notification.objects.create(
                    recipient=instance.requesting_doctor,
                    title='ABNORMAL Lab Results',
                    message=f'ABNORMAL results for test #{instance.request_number} ({instance.test.name}). Value: {instance.result_value}. Reference: {instance.test.normal_range}',
                    notification_type='error',
                    action_url=f'/laboratory/detail/{instance.id}/',
                    is_urgent=True
                )
        
        elif new_status == 'rejected':
            # Notify requesting doctor about rejection
            Notification.objects.create(
                recipient=instance.requesting_doctor,
                title='Lab Request Rejected',
                message=f'Lab request #{instance.request_number} has been rejected. Reason: {instance.rejection_reason}',
                notification_type='warning',
                action_url=f'/laboratory/detail/{instance.id}/'
            )
        
        # Log status change
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='update',
            model_name='LabRequest',
            object_id=str(instance.id),
            object_repr=instance.request_number,
            changes={'status': f'{old_status} -> {new_status}'},
            ip_address='',
            user_agent=''
        )


@receiver(post_save, sender=LabResult)
def lab_result_post_save(sender, instance, created, **kwargs):
    """
    Handle detailed lab result creation
    """
    if created:
        # Check if this component result is abnormal
        if instance.is_abnormal:
            # Notify requesting doctor
            Notification.objects.create(
                recipient=instance.lab_request.requesting_doctor,
                title='Abnormal Lab Component',
                message=f'Abnormal result for {instance.component_name}: {instance.result_value} {instance.unit} (Ref: {instance.reference_range})',
                notification_type='warning',
                action_url=f'/laboratory/detail/{instance.lab_request.id}/'
            )


def notify_lab_staff(lab_request, event):
    """
    Notify laboratory staff about new requests
    """
    try:
        # Get lab technicians
        lab_techs = User.objects.filter(role='lab')
        
        for tech in lab_techs:
            Notification.objects.create(
                recipient=tech,
                title='New Lab Request' if event == 'new' else 'Lab Request Update',
                message=f'New {lab_request.get_priority_display()} lab request #{lab_request.request_number} for {lab_request.test.name}. Patient: {lab_request.patient.full_name}',
                notification_type='info',
                action_url=f'/laboratory/requests/',
                is_urgent=(lab_request.priority == 'stat')
            )
    except Exception as e:
        print(f"Failed to notify lab staff: {e}")