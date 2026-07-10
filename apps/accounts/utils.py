"""
Utility functions for accounts app
"""
import random
import string
from django.core.mail import send_mail
from django.conf import settings


def generate_otp():
    """Generate a 6-digit OTP (One-Time Password)"""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp):
    """Send OTP via email for two-factor authentication"""
    try:
        send_mail(
            subject='MedLink EHR - Login Verification Code',
            message=f"""
            Dear User,

            Your verification code for MedLink EHR is: {otp}

            This code will expire in 5 minutes.

            If you did not request this code, please ignore this email or contact your system administrator.

            Best regards,
            MedLink EHR Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send OTP email to {email}: {e}")
        return False


def send_otp_sms(phone_number, otp):
    """Send OTP via SMS for two-factor authentication"""
    # In production, integrate with Africa's Talking, Twilio, or other SMS gateway
    # This is a placeholder implementation
    try:
        # Example with Africa's Talking (commented out)
        # import africastalking
        # africastalking.initialize(username='', api_key='')
        # sms = africastalking.SMS
        # response = sms.send(f"Your MedLink verification code is: {otp}", [phone_number])
        
        # For development, just print to console
        print(f"SMS to {phone_number}: Your MedLink verification code is: {otp}")
        return True
    except Exception as e:
        print(f"Failed to send OTP SMS to {phone_number}: {e}")
        return False


def generate_reset_token():
    """Generate a password reset token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def send_password_reset_email(email, token):
    """Send password reset email"""
    try:
        reset_link = f"{settings.SITE_URL}/reset-password/{token}/"
        send_mail(
            subject='MedLink EHR - Password Reset Request',
            message=f"""
            Dear User,

            You requested a password reset for your MedLink EHR account.

            Click the link below to reset your password:
            {reset_link}

            This link will expire in 1 hour.

            If you did not request this, please ignore this email.

            Best regards,
            MedLink EHR Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send password reset email to {email}: {e}")
        return False


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_user_activity(user, action, request, details=None):
    """Log user activity for audit purposes"""
    from .models import AuditLog
    
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name='User',
        object_id=str(user.id) if user else None,
        object_repr=str(user) if user else 'Anonymous',
        changes=details or {},
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )