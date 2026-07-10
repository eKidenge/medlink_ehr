"""
Signals for the admissions app - Handles bed management and discharge notifications
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Admission, Bed, Ward, DailyRound
from apps.dashboard.models import Notification
from apps.accounts.models import User


@receiver(post_save, sender=Admission)
def admission_post_save(sender, instance, created, **kwargs):
    """
    Handle admission creation and updates
    """
    if created:
        # Update bed occupancy
        if instance.bed:
            instance.bed.occupy(instance)
        
        # Update ward bed count
        if instance.ward:
            instance.ward.update_bed_counts()
        
        # Notify ward staff
        notify_ward_staff(instance, 'admitted')
        
        # Log admission
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='Admission',
            object_id=str(instance.id),
            object_repr=instance.admission_number,
            changes={
                'patient': instance.patient.full_name,
                'ward': instance.ward.name if instance.ward else None,
                'bed': instance.bed.bed_number if instance.bed else None,
                'diagnosis': instance.primary_diagnosis[:100] if instance.primary_diagnosis else ''
            },
            ip_address='',
            user_agent=''
        )
    
    elif instance.status == 'discharged' and hasattr(instance, '_discharging'):
        # Patient discharged - vacate bed
        if instance.bed:
            instance.bed.vacate()
        
        if instance.ward:
            instance.ward.update_bed_counts()
        
        # Notify ward staff
        notify_ward_staff(instance, 'discharged')
        
        # Log discharge
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='update',
            model_name='Admission',
            object_id=str(instance.id),
            object_repr=instance.admission_number,
            changes={
                'status': 'discharged',
                'discharge_status': instance.discharge_status,
                'discharge_date': str(instance.discharge_date)
            },
            ip_address='',
            user_agent=''
        )


@receiver(pre_save, sender=Admission)
def admission_pre_save(sender, instance, **kwargs):
    """
    Track discharge before save
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.status != 'discharged' and instance.status == 'discharged':
                instance._discharging = True
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=Bed)
def bed_post_save(sender, instance, created, **kwargs):
    """
    Handle bed updates
    """
    if created:
        # Update ward bed count
        instance.ward.update_bed_counts()
        
        # Log bed creation
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='Bed',
            object_id=str(instance.id),
            object_repr=f"Bed {instance.bed_number} in {instance.ward.name}",
            changes={
                'bed_number': instance.bed_number,
                'bed_type': instance.bed_type,
                'ward': instance.ward.name
            },
            ip_address='',
            user_agent=''
        )
    else:
        # Check if bed status changed
        if hasattr(instance, '_status_changed'):
            from apps.accounts.models import AuditLog
            AuditLog.objects.create(
                user=None,
                action='update',
                model_name='Bed',
                object_id=str(instance.id),
                object_repr=f"Bed {instance.bed_number}",
                changes=instance._status_changed,
                ip_address='',
                user_agent=''
            )


@receiver(post_save, sender=DailyRound)
def daily_round_post_save(sender, instance, created, **kwargs):
    """
    Handle daily round creation
    """
    if created:
        # Notify attending doctor
        if instance.admission.admitting_doctor and instance.admission.admitting_doctor != instance.doctor:
            Notification.objects.create(
                recipient=instance.admission.admitting_doctor,
                title='New Round Note Added',
                message=f'A new round note was added for patient {instance.admission.patient.full_name} by Dr. {instance.doctor.get_full_name()}',
                notification_type='info',
                action_url=f'/admissions/detail/{instance.admission.id}/'
            )
        
        # Log round
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='DailyRound',
            object_id=str(instance.id),
            object_repr=f"Round for {instance.admission.admission_number}",
            changes={
                'doctor': instance.doctor.get_full_name(),
                'assessment': instance.assessment[:100] if instance.assessment else ''
            },
            ip_address='',
            user_agent=''
        )


def notify_ward_staff(admission, event):
    """
    Notify ward staff about admission or discharge
    """
    try:
        # Get ward nurses
        ward_nurses = User.objects.filter(
            role='nurse',
            department=admission.ward
        )
        
        if event == 'admitted':
            title = 'New Patient Admitted'
            message = f'Patient {admission.patient.full_name} has been admitted to {admission.ward.name}, Bed {admission.bed.bed_number if admission.bed else "TBD"}. Diagnosis: {admission.primary_diagnosis[:100]}'
            action_url = f'/admissions/detail/{admission.id}/'
        else:  # discharged
            title = 'Patient Discharged'
            message = f'Patient {admission.patient.full_name} has been discharged from {admission.ward.name}. Status: {admission.get_discharge_status_display()}'
            action_url = f'/admissions/detail/{admission.id}/'
        
        for nurse in ward_nurses:
            Notification.objects.create(
                recipient=nurse,
                title=title,
                message=message,
                notification_type='info',
                action_url=action_url
            )
    except Exception as e:
        print(f"Failed to notify ward staff: {e}")