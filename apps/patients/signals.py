"""
Signals for the patients app - Handles QR code generation, patient merging, and medical flags
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import qrcode
from io import BytesIO
from django.core.files import File
import json
from .models import Patient, PatientAllergy, PatientChronicDisease, PatientVaccination


@receiver(post_save, sender=Patient)
def patient_post_save(sender, instance, created, **kwargs):
    """
    Handle patient creation and updates
    """
    if created:
        # Auto-generate QR code
        generate_patient_qr_code(instance)
        
        # Send SMS notification (in production, use SMS gateway)
        if instance.phone_primary:
            send_sms_notification(
                instance.phone_primary,
                f"Dear {instance.first_name}, you have been registered at MedLink EHR. Your patient number is {instance.patient_number}. Please save this for future reference."
            )
        
        # Create initial medical record audit
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,  # Will be set from request
            action='create',
            model_name='Patient',
            object_id=str(instance.id),
            object_repr=str(instance),
            changes={
                'patient_number': instance.patient_number,
                'name': instance.full_name,
                'phone': instance.phone_primary
            },
            ip_address='',
            user_agent=''
        )
    else:
        # Check if patient was merged
        if instance.merged_to and not hasattr(instance, '_merging_processed'):
            instance._merging_processed = True
            # Log merge
            from apps.accounts.models import AuditLog
            AuditLog.objects.create(
                user=None,
                action='update',
                model_name='Patient',
                object_id=str(instance.id),
                object_repr=str(instance),
                changes={'merged_to': instance.merged_to.patient_number, 'is_merged': True},
                ip_address='',
                user_agent=''
            )


@receiver(pre_save, sender=Patient)
def patient_pre_save(sender, instance, **kwargs):
    """
    Track patient changes before save
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            changes = {}
            
            # Track critical field changes
            critical_fields = ['first_name', 'last_name', 'phone_primary', 'nhif_number', 'identification_number']
            for field in critical_fields:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = {'old': str(old_value), 'new': str(new_value)}
            
            # Track medical flag changes
            medical_flags = ['has_allergies', 'has_chronic_diseases', 'is_pregnant', 'is_deceased']
            for field in medical_flags:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}
            
            instance._pending_changes = changes
        except sender.DoesNotExist:
            instance._pending_changes = {}


@receiver(post_save, sender=Patient)
def patient_update_audit(sender, instance, created, **kwargs):
    """
    Audit patient updates
    """
    if not created and hasattr(instance, '_pending_changes') and instance._pending_changes:
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='update',
            model_name='Patient',
            object_id=str(instance.id),
            object_repr=str(instance),
            changes=instance._pending_changes,
            ip_address='',
            user_agent=''
        )


def generate_patient_qr_code(patient):
    """
    Generate QR code for patient
    """
    try:
        qr_data = {
            'patient_number': patient.patient_number,
            'mrn': patient.mrn_number,
            'name': patient.full_name,
            'phone': patient.phone_primary,
            'nhif': patient.nhif_number or '',
            'blood_type': patient.blood_type or '',
            'allergies': [a.allergen for a in patient.allergies.filter(severity__in=['severe', 'life_threatening'])]
        }
        
        qr_text = json.dumps(qr_data)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"qr_{patient.patient_number}.png"
        patient.qr_code.save(filename, File(buffer), save=False)
        patient.qr_code_data = qr_text
        patient.save(update_fields=['qr_code', 'qr_code_data'])
    except Exception as e:
        print(f"Failed to generate QR code for patient {patient.id}: {e}")


@receiver(post_save, sender=PatientAllergy)
def allergy_post_save(sender, instance, created, **kwargs):
    """
    Handle allergy addition - update patient flag and send alerts
    """
    if created:
        # Update patient has_allergies flag
        patient = instance.patient
        if not patient.has_allergies:
            patient.has_allergies = True
            patient.save(update_fields=['has_allergies'])
        
        # Create audit log
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='PatientAllergy',
            object_id=str(instance.id),
            object_repr=f"Allergy: {instance.allergen}",
            changes={
                'patient': patient.full_name,
                'allergen': instance.allergen,
                'severity': instance.severity,
                'reaction': instance.reaction
            },
            ip_address='',
            user_agent=''
        )
        
        # Send alert for severe allergies
        if instance.severity in ['severe', 'life_threatening']:
            # In production, send to clinical team
            send_alert_notification(
                f"CRITICAL: Patient {patient.full_name} has {instance.severity} allergy to {instance.allergen}",
                priority='high'
            )


@receiver(post_delete, sender=PatientAllergy)
def allergy_post_delete(sender, instance, **kwargs):
    """
    Handle allergy deletion - update patient flag if no allergies remain
    """
    patient = instance.patient
    if not patient.allergies.exists():
        patient.has_allergies = False
        patient.save(update_fields=['has_allergies'])


@receiver(post_save, sender=PatientChronicDisease)
def chronic_disease_post_save(sender, instance, created, **kwargs):
    """
    Handle chronic disease addition
    """
    if created:
        # Update patient has_chronic_diseases flag
        patient = instance.patient
        if not patient.has_chronic_diseases:
            patient.has_chronic_diseases = True
            patient.save(update_fields=['has_chronic_diseases'])
        
        # Create audit log
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='PatientChronicDisease',
            object_id=str(instance.id),
            object_repr=f"Chronic: {instance.disease_name}",
            changes={
                'patient': patient.full_name,
                'disease': instance.disease_name,
                'diagnosed_date': str(instance.diagnosed_date),
                'status': instance.status
            },
            ip_address='',
            user_agent=''
        )


@receiver(post_delete, sender=PatientChronicDisease)
def chronic_disease_post_delete(sender, instance, **kwargs):
    """
    Handle chronic disease deletion - update patient flag
    """
    patient = instance.patient
    if not patient.chronic_diseases.exists():
        patient.has_chronic_diseases = False
        patient.save(update_fields=['has_chronic_diseases'])


@receiver(post_save, sender=PatientVaccination)
def vaccination_post_save(sender, instance, created, **kwargs):
    """
    Handle vaccination addition - check for due dates
    """
    if created:
        # Create audit log
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='PatientVaccination',
            object_id=str(instance.id),
            object_repr=f"Vaccine: {instance.vaccine_name}",
            changes={
                'patient': instance.patient.full_name,
                'vaccine': instance.vaccine_name,
                'dose': instance.dose_number,
                'date': str(instance.date_administered),
                'next_due': str(instance.next_due_date) if instance.next_due_date else None
            },
            ip_address='',
            user_agent=''
        )
        
        # Schedule reminder for next dose
        if instance.next_due_date:
            schedule_vaccination_reminder(instance)


def schedule_vaccination_reminder(vaccination):
    """
    Schedule a reminder for next vaccination dose
    """
    # In production, use Celery beat for scheduling
    from datetime import date
    from apps.dashboard.models import Notification
    
    # Create notification for patient (if patient portal exists)
    # For now, we'll just log it
    print(f"Vaccination reminder scheduled for {vaccination.patient.full_name} on {vaccination.next_due_date}")


def send_sms_notification(phone_number, message):
    """
    Send SMS notification (placeholder - integrate with SMS gateway)
    """
    # In production, integrate with Africa's Talking, Twilio, etc.
    print(f"SMS to {phone_number}: {message}")


def send_alert_notification(message, priority='normal'):
    """
    Send alert notification to clinical team
    """
    # In production, send to dashboard, email, or SMS
    print(f"ALERT ({priority}): {message}")
    
    # Create dashboard notification
    try:
        from apps.dashboard.models import Notification
        from apps.accounts.models import User
        
        # Send to admin users
        admins = User.objects.filter(role__in=['admin', 'super_admin', 'doctor'])
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title='Patient Alert' if priority == 'normal' else 'CRITICAL Patient Alert',
                message=message,
                notification_type='error' if priority == 'high' else 'warning',
                is_urgent=(priority == 'high')
            )
    except Exception as e:
        print(f"Failed to create notification: {e}")