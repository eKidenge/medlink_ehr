"""
Signals for the pharmacy app - Handles prescriptions and inventory
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Prescription, StockTransaction, Medication
from apps.dashboard.models import Notification
from apps.accounts.models import User


@receiver(post_save, sender=Prescription)
def prescription_post_save(sender, instance, created, **kwargs):
    """
    Handle prescription creation and updates
    """
    if created:
        # Notify pharmacist about new prescription
        notify_pharmacy_staff(instance, 'new')
        
        # Check for drug interactions and allergies
        alerts = instance.check_safety_alerts()
        if alerts:
            # Send alerts to prescribing doctor
            for alert in alerts:
                Notification.objects.create(
                    recipient=instance.prescribing_doctor,
                    title=f'Medication Alert: {alert["type"].upper()}',
                    message=alert['message'],
                    notification_type='error' if alert['severity'] in ['severe', 'life_threatening'] else 'warning',
                    action_url=f'/pharmacy/detail/{instance.id}/',
                    is_urgent=(alert['severity'] == 'life_threatening')
                )
        
        # Log creation
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='Prescription',
            object_id=str(instance.id),
            object_repr=instance.prescription_number,
            changes={
                'patient': instance.patient.full_name,
                'medication': instance.medication.generic_name,
                'dosage': instance.dosage,
                'quantity': instance.quantity
            },
            ip_address='',
            user_agent=''
        )
    
    elif instance.status == 'dispensed' and hasattr(instance, '_dispensing'):
        # Prescription dispensed - update stock and notify doctor
        Notification.objects.create(
            recipient=instance.prescribing_doctor,
            title='Prescription Dispensed',
            message=f'Prescription #{instance.prescription_number} for {instance.medication.generic_name} has been dispensed. Quantity: {instance.dispensed_quantity}',
            notification_type='success',
            action_url=f'/pharmacy/detail/{instance.id}/'
        )
        
        # Log dispensing
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='update',
            model_name='Prescription',
            object_id=str(instance.id),
            object_repr=instance.prescription_number,
            changes={
                'status': 'dispensed',
                'dispensed_by': instance.dispensed_by.get_full_name() if instance.dispensed_by else None,
                'dispensed_quantity': instance.dispensed_quantity
            },
            ip_address='',
            user_agent=''
        )


@receiver(pre_save, sender=Prescription)
def prescription_pre_save(sender, instance, **kwargs):
    """
    Track dispensing before save
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.status != 'dispensed' and instance.status == 'dispensed':
                instance._dispensing = True
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=StockTransaction)
def stock_transaction_post_save(sender, instance, created, **kwargs):
    """
    Handle stock transactions - check low stock alerts
    """
    if created:
        # Check if medication is now low stock
        medication = instance.medication
        if medication.is_low_stock():
            # Notify pharmacy manager
            notify_low_stock(medication)
        
        # Log transaction
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='StockTransaction',
            object_id=str(instance.id),
            object_repr=f"Stock {instance.get_transaction_type_display()}",
            changes={
                'medication': medication.generic_name,
                'quantity': instance.quantity,
                'type': instance.transaction_type,
                'stock_after': instance.stock_after
            },
            ip_address='',
            user_agent=''
        )


@receiver(post_save, sender=Medication)
def medication_post_save(sender, instance, created, **kwargs):
    """
    Handle medication updates
    """
    if created:
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=None,
            action='create',
            model_name='Medication',
            object_id=str(instance.id),
            object_repr=instance.generic_name,
            changes={
                'generic_name': instance.generic_name,
                'category': instance.category,
                'unit_price': instance.unit_price
            },
            ip_address='',
            user_agent=''
        )
    else:
        # Check if expiry date is approaching
        if instance.expiry_date:
            from datetime import date
            days_until_expiry = (instance.expiry_date - date.today()).days
            if days_until_expiry <= 30 and days_until_expiry > 0:
                notify_expiring_medication(instance, days_until_expiry)


def notify_pharmacy_staff(prescription, event):
    """
    Notify pharmacy staff about prescriptions
    """
    try:
        pharmacists = User.objects.filter(role='pharmacy')
        
        for pharmacist in pharmacists:
            Notification.objects.create(
                recipient=pharmacist,
                title='New Prescription' if event == 'new' else 'Prescription Update',
                message=f'New prescription #{prescription.prescription_number} for {prescription.medication.generic_name}. Patient: {prescription.patient.full_name}',
                notification_type='info',
                action_url=f'/pharmacy/prescriptions/'
            )
    except Exception as e:
        print(f"Failed to notify pharmacy staff: {e}")


def notify_low_stock(medication):
    """
    Notify pharmacy manager about low stock
    """
    try:
        pharmacy_managers = User.objects.filter(role__in=['admin', 'pharmacy'])
        
        for manager in pharmacy_managers:
            Notification.objects.create(
                recipient=manager,
                title='Low Stock Alert',
                message=f'Medication {medication.generic_name} is low on stock. Current stock: {medication.current_stock}. Reorder level: {medication.reorder_level}',
                notification_type='warning',
                action_url=f'/pharmacy/inventory/',
                is_urgent=(medication.current_stock <= medication.reorder_level / 2)
            )
    except Exception as e:
        print(f"Failed to notify low stock: {e}")


def notify_expiring_medication(medication, days_until_expiry):
    """
    Notify about expiring medication
    """
    try:
        pharmacy_managers = User.objects.filter(role__in=['admin', 'pharmacy'])
        
        for manager in pharmacy_managers:
            Notification.objects.create(
                recipient=manager,
                title='Medication Expiring Soon',
                message=f'Medication {medication.generic_name} (Batch: {medication.batch_number}) will expire in {days_until_expiry} days on {medication.expiry_date}.',
                notification_type='warning',
                action_url=f'/pharmacy/inventory/'
            )
    except Exception as e:
        print(f"Failed to notify expiring medication: {e}")