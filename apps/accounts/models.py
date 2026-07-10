from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
import uuid


class Department(models.Model):
    """Hospital department model"""
    
    DEPT_TYPES = (
        ('outpatient', 'Outpatient'),
        ('inpatient', 'Inpatient'),
        ('emergency', 'Emergency'),
        ('laboratory', 'Laboratory'),
        ('radiology', 'Radiology'),
        ('pharmacy', 'Pharmacy'),
        ('records', 'Medical Records'),
        ('administration', 'Administration'),
        ('finance', 'Finance'),
        ('hr', 'Human Resources'),
    )
    
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=DEPT_TYPES)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='managed_departments')
    parent_department = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name[:3].upper() + str(uuid.uuid4().hex[:4]).upper()
        super().save(*args, **kwargs)


class User(AbstractUser):
    """Custom User Model with enhanced fields"""
    
    ROLE_CHOICES = (
        ('super_admin', 'Super Administrator'),
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('clinical_officer', 'Clinical Officer'),
        ('lab_technician', 'Laboratory Technician'),
        ('pharmacist', 'Pharmacist'),
        ('pharmacy_tech', 'Pharmacy Technician'),
        ('records_officer', 'Medical Records Officer'),
        ('cashier', 'Cashier'),
        ('receptionist', 'Receptionist'),
        ('ward_clerk', 'Ward Clerk'),
        ('manager', 'Manager'),
        ('viewer', 'View Only'),
    )
    
    TITLE_CHOICES = (
        ('dr', 'Dr.'),
        ('nurse', 'Nurse'),
        ('mr', 'Mr.'),
        ('mrs', 'Mrs.'),
        ('ms', 'Ms.'),
        ('prof', 'Prof.'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    # Personal Information
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    national_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    employee_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')], blank=True, default='')
    alternate_phone = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)  # ADDED THIS FIELD
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    
    # Professional Information
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    specialization = models.CharField(max_length=200, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    
    # Employment Details
    date_joined_organization = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=50, choices=(
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
        ('volunteer', 'Volunteer'),
    ), default='full_time')
    
    # Permissions and Status
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(default=timezone.now)
    login_attempts = models.IntegerField(default=0)
    account_locked = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(auto_now_add=True)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=100, blank=True)
    
    # Notifications
    receive_email_notifications = models.BooleanField(default=True)
    receive_sms_notifications = models.BooleanField(default=False)
    receive_whatsapp_notifications = models.BooleanField(default=False)
    
    # Audit
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users')
    updated_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['first_name', 'last_name']
        permissions = [
            ('can_manage_users', 'Can manage users'),
            ('can_view_audit_logs', 'Can view audit logs'),
            ('can_export_data', 'Can export data'),
            ('can_manage_system', 'Can manage system settings'),
        ]
    
    def __str__(self):
        title_prefix = f"{self.get_title_display()} " if self.title else ""
        return f"{title_prefix}{self.get_full_name()} ({self.get_role_display()})"
    
    def get_full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        if not self.employee_number:
            year = timezone.now().year
            count = User.objects.filter(employee_number__startswith=f"EMP{year}").count() + 1
            self.employee_number = f"EMP{year}{count:05d}"
        super().save(*args, **kwargs)
    
    def increment_login_attempts(self):
        self.login_attempts += 1
        if self.login_attempts >= 5:
            self.account_locked = True
        self.save(update_fields=['login_attempts', 'account_locked'])
    
    def reset_login_attempts(self):
        self.login_attempts = 0
        self.account_locked = False
        self.save(update_fields=['login_attempts', 'account_locked'])
    
    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.is_online = True
        self.save(update_fields=['last_activity', 'is_online'])


class UserSession(models.Model):
    """Track user sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=100, unique=True, null=True, blank=True)  # Allow null for API logins
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class AuditLog(models.Model):
    """System audit log"""
    
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('print', 'Print'),
        ('download', 'Download'),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} - {self.timestamp}"