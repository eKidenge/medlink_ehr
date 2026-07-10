"""
Signals for the referrals app - Handles referral tracking and notifications
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Referral, ReferralNote
from apps.dashboard.models import Notification
from apps.accounts.models import User


@receiver(post_save, sender=Referral)
def referral_post_save(sender, instance, created, **kwargs):
    """
    Handle referral creation and status changes
    """
    if created:
        # Notify referring doctor
        Notification.objects.create(
            recipient=instance.referring_doctor,
            title='Referral Created',
            message=f'Referral #{instance.referral_number} has been created for patient {instance.patient.full_name} to {instance.receiving_facility}.',
            notification_type='info',
            action_url=f'/referrals/detail/{instance.id}/'
        )
        
        # Log creation
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='Referral',
            object_id=str(instance.id),
            object_repr=instance.referral_number,
            changes={
                'patient': instance.patient.full_name,
                'to_facility': instance.receiving_facility,
                'reason': instance.reason_for_referral[:100] if instance.reason_for_referral else ''
            },
            ip_address='',
            user_agent=''
        )
    
    # Check for status changes
    if hasattr(instance, '_status_changed'):
        old_status, new_status = instance._status_changed
        
        if new_status == 'approved':
            # Notify referring doctor
            Notification.objects.create(
                recipient=instance.referring_doctor,
                title='Referral Approved',
                message=f'Referral #{instance.referral_number} has been approved.',
                notification_type='success',
                action_url=f'/referrals/detail/{instance.id}/'
            )
            
            # Generate QR code for secure access
            generate_referral_qr_code(instance)
        
        elif new_status == 'completed':
            # Notify referring doctor
            Notification.objects.create(
                recipient=instance.referring_doctor,
                title='Referral Completed',
                message=f'Referral #{instance.referral_number} has been marked as completed. Outcome: {instance.outcome[:100] if instance.outcome else "Not specified"}',
                notification_type='success',
                action_url=f'/referrals/detail/{instance.id}/'
            )
        
        elif new_status == 'cancelled':
            # Notify referring doctor
            Notification.objects.create(
                recipient=instance.referring_doctor,
                title='Referral Cancelled',
                message=f'Referral #{instance.referral_number} has been cancelled. Reason: {instance.cancelled_reason}',
                notification_type='warning',
                action_url=f'/referrals/detail/{instance.id}/'
            )
        
        # Log status change
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='update',
            model_name='Referral',
            object_id=str(instance.id),
            object_repr=instance.referral_number,
            changes={'status': f'{old_status} -> {new_status}'},
            ip_address='',
            user_agent=''
        )


@receiver(post_save, sender=ReferralNote)
def referral_note_post_save(sender, instance, created, **kwargs):
    """
    Handle referral note creation
    """
    if created:
        # Notify referring doctor
        if instance.author != instance.referral.referring_doctor:
            Notification.objects.create(
                recipient=instance.referral.referring_doctor,
                title='New Referral Note',
                message=f'A new note has been added to referral #{instance.referral.referral_number} by {instance.author.get_full_name()}.',
                notification_type='info',
                action_url=f'/referrals/detail/{instance.referral.id}/'
            )
        
        # Log note creation
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='ReferralNote',
            object_id=str(instance.id),
            object_repr=f"Note for {instance.referral.referral_number}",
            changes={
                'author': instance.author.get_full_name(),
                'note_preview': instance.note[:100] if instance.note else ''
            },
            ip_address='',
            user_agent=''
        )


def generate_referral_qr_code(referral):
    """
    Generate QR code for secure referral access
    """
    try:
        import qrcode
        import json
        import secrets
        from io import BytesIO
        from django.core.files import File
        
        # Generate unique access token
        token = secrets.token_urlsafe(32)
        referral.access_token = token
        referral.token_expiry = timezone.now() + timezone.timedelta(days=7)
        
        # Create QR code data
        qr_data = {
            'referral_number': referral.referral_number,
            'token': token,
            'patient_name': referral.patient.full_name,
            'receiving_facility': referral.receiving_facility,
            'created_at': referral.created_at.isoformat()
        }
        
        qr_text = json.dumps(qr_data)
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"referral_qr_{referral.referral_number}.png"
        referral.qr_code.save(filename, File(buffer), save=False)
        referral.save()
        
    except Exception as e:
        print(f"Failed to generate QR code for referral {referral.referral_number}: {e}")