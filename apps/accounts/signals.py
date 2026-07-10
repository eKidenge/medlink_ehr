"""
Signals for the accounts app - Handles user activity tracking, audit logging, and notifications
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError
import uuid
from .models import User, UserSession, AuditLog


def get_client_ip(request):
    """
    Get client IP address from request
    """
    if request is None:
        return '0.0.0.0'
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip or '0.0.0.0'


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Handle user creation and updates
    """
    if created:
        # Send welcome email to new user
        if instance.email:
            try:
                send_mail(
                    subject='Welcome to MedLink EHR System',
                    message=f"""
                    Dear {instance.get_full_name() or instance.username},

                    Welcome to the MedLink Electronic Health Record System.

                    Your account has been created with the following details:
                    Username: {instance.username}
                    Role: {instance.get_role_display()}

                    Please log in and change your password immediately.

                    Best regards,
                    MedLink EHR Team
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Failed to send welcome email: {e}")
        
        # Create audit log for user creation - FIXED: provide default values
        AuditLog.objects.create(
            user=None,  # System created
            action='create',
            model_name='User',
            object_id=str(instance.id),
            object_repr=str(instance),
            changes={'username': instance.username, 'email': instance.email, 'role': instance.role},
            ip_address='0.0.0.0',  # Default IP for system actions
            user_agent='System'     # Default user agent for system actions
        )


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    """
    Track changes before user update
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            changes = {}
            
            # Track field changes
            fields_to_track = ['first_name', 'last_name', 'email', 'phone_number', 'role', 'department', 'is_active']
            for field in fields_to_track:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = {'old': str(old_value), 'new': str(new_value)}
            
            instance._pending_changes = changes
        except sender.DoesNotExist:
            instance._pending_changes = {}


@receiver(post_save, sender=User)
def user_update_audit(sender, instance, created, **kwargs):
    """
    Audit user updates
    """
    if not created and hasattr(instance, '_pending_changes') and instance._pending_changes:
        AuditLog.objects.create(
            user=None,  # Will be set from request context
            action='update',
            model_name='User',
            object_id=str(instance.id),
            object_repr=str(instance),
            changes=instance._pending_changes,
            ip_address='0.0.0.0',  # Default for system updates
            user_agent='System'
        )


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """
    Handle user login - update online status and create session
    """
    # Update user status
    user.is_online = True
    user.last_activity = timezone.now()
    user.reset_login_attempts()
    user.save(update_fields=['is_online', 'last_activity', 'login_attempts'])
    
    # Get client IP
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else 'Unknown'
    
    # Get session key, generate if None
    session_key = request.session.session_key if request and request.session.session_key else str(uuid.uuid4())
    
    # Create session record with duplicate handling
    try:
        UserSession.objects.create(
            user=user,
            session_key=session_key,
            ip_address=client_ip,
            user_agent=user_agent,
            login_time=timezone.now()
        )
    except IntegrityError:
        # Session key already exists, generate a new unique one
        new_session_key = str(uuid.uuid4())
        UserSession.objects.create(
            user=user,
            session_key=new_session_key,
            ip_address=client_ip,
            user_agent=user_agent,
            login_time=timezone.now()
        )
    
    # Create audit log
    AuditLog.objects.create(
        user=user,
        action='login',
        model_name='User',
        object_id=str(user.id),
        object_repr=str(user),
        changes={'ip_address': client_ip},
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # Send notification for first login from new IP (optional)
    check_suspicious_login(user, client_ip)


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """
    Handle user logout - update online status and close session
    """
    if user:
        user.is_online = False
        user.save(update_fields=['is_online'])
        
        # Close session
        if request and request.session.session_key:
            UserSession.objects.filter(
                session_key=request.session.session_key,
                is_active=True
            ).update(is_active=False, logout_time=timezone.now())
        
        # Create audit log
        client_ip = get_client_ip(request) if request else '0.0.0.0'
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else 'Unknown'
        
        AuditLog.objects.create(
            user=user,
            action='logout',
            model_name='User',
            object_id=str(user.id),
            object_repr=str(user),
            changes={},
            ip_address=client_ip,
            user_agent=user_agent
        )


@receiver(user_login_failed)
def user_login_failed_handler(sender, credentials, request, **kwargs):
    """
    Track failed login attempts
    """
    username = credentials.get('username') if credentials else None
    client_ip = get_client_ip(request) if request else '0.0.0.0'
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else 'Unknown'
    
    if username:
        try:
            user = User.objects.get(username=username)
            user.increment_login_attempts()
            
            # Create audit log for failed attempt
            AuditLog.objects.create(
                user=user,
                action='login',
                model_name='User',
                object_id=str(user.id),
                object_repr=str(user),
                changes={'success': False, 'attempt': user.login_attempts},
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            # Lock account after 5 failed attempts
            if user.login_attempts >= 5 and not user.account_locked:
                user.account_locked = True
                user.save(update_fields=['account_locked'])
                
                # Send alert email
                if user.email:
                    send_mail(
                        subject='Account Locked - MedLink EHR',
                        message=f"""
                        Dear {user.get_full_name() or user.username},

                        Your account has been locked due to 5 failed login attempts.

                        Please contact your system administrator to unlock your account.

                        Best regards,
                        MedLink EHR Team
                        """,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
        except User.DoesNotExist:
            # Log failed attempt for non-existent user
            AuditLog.objects.create(
                user=None,
                action='login',
                model_name='User',
                object_id='',
                object_repr=f'Unknown user: {username}',
                changes={'success': False},
                ip_address=client_ip,
                user_agent=user_agent
            )


@receiver(post_delete, sender=User)
def user_post_delete(sender, instance, **kwargs):
    """
    Handle user deletion - archive records
    """
    AuditLog.objects.create(
        user=None,
        action='delete',
        model_name='User',
        object_id=str(instance.id),
        object_repr=str(instance),
        changes={'deleted_user': instance.username},
        ip_address='0.0.0.0',
        user_agent='System'
    )


def check_suspicious_login(user, ip_address):
    """
    Check for suspicious login patterns
    """
    if not user or not ip_address:
        return
    
    # Get last 5 logins
    recent_logins = UserSession.objects.filter(
        user=user,
        is_active=False
    ).order_by('-login_time')[:5]
    
    # Check if IP is new
    known_ips = UserSession.objects.filter(user=user).values_list('ip_address', flat=True).distinct()
    if ip_address not in known_ips:
        # Send notification email
        if user.email:
            try:
                send_mail(
                    subject='New Login Location Detected - MedLink EHR',
                    message=f"""
                    Dear {user.get_full_name() or user.username},

                    A login to your account was detected from a new IP address: {ip_address}

                    If this was you, no action is required.
                    If you did not authorize this login, please contact your system administrator immediately.

                    Best regards,
                    MedLink EHR Team
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Failed to send suspicious login email: {e}")