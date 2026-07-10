"""
Signals for the visits app - Handles visit workflow and notifications
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Visit, ClinicalNote, Vitals
from apps.dashboard.models import Notification
from apps.accounts.models import User


@receiver(pre_save, sender=Visit)
def visit_pre_save(sender, instance, **kwargs):
    """
    Track visit status changes
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                instance._status_changed = {
                    'old': old_instance.status,
                    'new': instance.status
                }
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=Visit)
def visit_post_save(sender, instance, created, **kwargs):
    """
    Handle visit creation and status changes
    """
    if created:
        # Create notification for doctor if assigned
        if instance.primary_doctor:
            Notification.objects.create(
                recipient=instance.primary_doctor,
                title='New Patient Assigned',
                message=f'Patient {instance.patient.full_name} has been assigned to you. Visit #: {instance.visit_number}',
                notification_type='info',
                action_url=f'/visits/detail/{instance.id}/'
            )
        
        # Log creation
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='Visit',
            object_id=str(instance.id),
            object_repr=instance.visit_number,
            changes={
                'patient': instance.patient.full_name,
                'visit_type': instance.visit_type,
                'chief_complaint': instance.chief_complaint[:100] if instance.chief_complaint else ''
            },
            ip_address='',
            user_agent=''
        )
    
    elif hasattr(instance, '_status_changed'):
        # Status changed - send notifications
        old_status = instance._status_changed['old']
        new_status = instance._status_changed['new']
        
        # Notify appropriate parties
        if new_status == 'check_in':
            # Notify triage team
            notify_triage_team(instance)
        elif new_status == 'consultation' and instance.primary_doctor:
            # Notify doctor that patient is ready
            Notification.objects.create(
                recipient=instance.primary_doctor,
                title='Patient Ready for Consultation',
                message=f'Patient {instance.patient.full_name} is ready for consultation. Visit #: {instance.visit_number}',
                notification_type='info',
                action_url=f'/visits/detail/{instance.id}/',
                is_urgent=(instance.priority in ['emergency', 'critical'])
            )
        elif new_status == 'completed':
            # Notify patient (if SMS configured)
            send_visit_completion_notification(instance)
        
        # Log status change
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='update',
            model_name='Visit',
            object_id=str(instance.id),
            object_repr=instance.visit_number,
            changes={'status': f'{old_status} -> {new_status}'},
            ip_address='',
            user_agent=''
        )


@receiver(post_save, sender=ClinicalNote)
def clinical_note_post_save(sender, instance, created, **kwargs):
    """
    Handle clinical note creation - notify relevant parties
    """
    if created:
        # Notify the visit's doctor that a note was added
        if instance.visit.primary_doctor and instance.visit.primary_doctor != instance.author:
            Notification.objects.create(
                recipient=instance.visit.primary_doctor,
                title='New Clinical Note Added',
                message=f'A new {instance.note_type} note was added for patient {instance.visit.patient.full_name} by {instance.author.get_full_name()}',
                notification_type='info',
                action_url=f'/visits/detail/{instance.visit.id}/'
            )
        
        # Log note creation
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='ClinicalNote',
            object_id=str(instance.id),
            object_repr=f"Note for {instance.visit.visit_number}",
            changes={
                'type': instance.note_type,
                'author': instance.author.get_full_name()
            },
            ip_address='',
            user_agent=''
        )


@receiver(post_save, sender=Vitals)
def vitals_post_save(sender, instance, created, **kwargs):
    """
    Handle vitals recording - check for critical values
    """
    if created and instance.is_critical():
        # Critical vitals detected - send immediate alert
        message = f"CRITICAL VITALS for patient {instance.visit.patient.full_name}: "
        if instance.temperature and (instance.temperature < 35 or instance.temperature > 39):
            message += f"Temperature: {instance.temperature}°C, "
        if instance.systolic_bp and instance.systolic_bp < 90:
            message += f"BP: {instance.systolic_bp}/{instance.diastolic_bp}, "
        if instance.oxygen_saturation and instance.oxygen_saturation < 90:
            message += f"O2 Sat: {instance.oxygen_saturation}%, "
        if instance.glasgow_coma_score and instance.glasgow_coma_score < 13:
            message += f"GCS: {instance.glasgow_coma_score}, "
        
        # Send to doctor and nurse
        if instance.visit.primary_doctor:
            Notification.objects.create(
                recipient=instance.visit.primary_doctor,
                title='CRITICAL VITALS ALERT',
                message=message,
                notification_type='error',
                action_url=f'/visits/detail/{instance.visit.id}/',
                is_urgent=True
            )
        
        if instance.visit.nurse:
            Notification.objects.create(
                recipient=instance.visit.nurse,
                title='CRITICAL VITALS ALERT',
                message=message,
                notification_type='error',
                action_url=f'/visits/detail/{instance.visit.id}/',
                is_urgent=True
            )


def notify_triage_team(visit):
    """
    Notify triage team about new patient
    """
    try:
        triage_nurses = User.objects.filter(role='nurse', department__type='emergency')
        for nurse in triage_nurses:
            Notification.objects.create(
                recipient=nurse,
                title='New Patient Waiting for Triage',
                message=f'Patient {visit.patient.full_name} has been checked in and is waiting for triage. Priority: {visit.priority}',
                notification_type='info',
                action_url=f'/triage/waiting/',
                is_urgent=(visit.priority in ['emergency', 'critical'])
            )
    except Exception as e:
        print(f"Failed to notify triage team: {e}")


def send_visit_completion_notification(visit):
    """
    Send notification about visit completion
    """
    # In production, send SMS to patient if configured
    if visit.patient.phone_primary:
        print(f"SMS to {visit.patient.phone_primary}: Your visit has been completed. Discharge instructions: {visit.discharge_instructions[:100] if visit.discharge_instructions else 'Please see reception'}")