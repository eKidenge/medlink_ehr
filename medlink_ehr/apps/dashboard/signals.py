"""
Signals for the dashboard app - Handles notifications and dashboard updates
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Notification, UserDashboard, DashboardWidget


@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    """
    Handle notification creation - real-time updates
    """
    if created:
        # In production, use WebSockets or Server-Sent Events for real-time updates
        # For now, just log
        print(f"New notification for {instance.recipient.get_full_name()}: {instance.title}")
        
        # Mark as urgent if needed
        if instance.is_urgent:
            # In production, send SMS or email for urgent notifications
            if instance.recipient.email:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    send_mail(
                        subject=f'URGENT: {instance.title}',
                        message=instance.message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[instance.recipient.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Failed to send urgent email: {e}")


@receiver(post_save, sender=UserDashboard)
def user_dashboard_post_save(sender, instance, created, **kwargs):
    """
    Handle user dashboard creation
    """
    if created:
        # Create default dashboard layout
        default_widgets = DashboardWidget.objects.filter(is_visible=True)[:6]
        for order, widget in enumerate(default_widgets):
            from .models import UserDashboardWidget
            UserDashboardWidget.objects.create(
                user_dashboard=instance,
                widget=widget,
                order=order
            )


@receiver(pre_delete, sender=Notification)
def notification_pre_delete(sender, instance, **kwargs):
    """
    Handle notification deletion - cleanup
    """
    # Log notification deletion for audit
    from apps.accounts.models import AuditLog
    AuditLog.objects.create(
        user=None,
        action='delete',
        model_name='Notification',
        object_id=str(instance.id),
        object_repr=instance.title,
        changes={'recipient': instance.recipient.username},
        ip_address='',
        user_agent=''
    )