from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count
from django.contrib import messages
import json

from .models import Department, User, UserSession, AuditLog


# ============================================================
# CUSTOM FORMS
# ============================================================

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'department')


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


# ============================================================
# DEPARTMENT ADMIN
# ============================================================

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'type', 'head_of_department',
        'parent_department', 'user_count', 'is_active', 'created_at',
    )
    list_filter = ('type', 'is_active', 'created_at')
    search_fields = ('code', 'name', 'description', 'head_of_department__username')
    readonly_fields = ('created_at', 'updated_at', 'user_count_display')
    list_select_related = ('head_of_department', 'parent_department')
    list_per_page = 25
    ordering = ('name',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'type', 'description')
        }),
        ('Hierarchy', {
            'fields': ('parent_department', 'head_of_department')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'user_count_display'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_departments', 'deactivate_departments']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_user_count=Count('users'))

    @admin.display(description='Users', ordering='_user_count')
    def user_count(self, obj):
        count = getattr(obj, '_user_count', 0)
        url = reverse('admin:accounts_user_changelist') + f'?department__id__exact={obj.id}'
        return format_html('<a href="{}">{} users</a>', url, count)

    @admin.display(description='User Count')
    def user_count_display(self, obj):
        if obj and obj.pk:
            return obj.users.count()
        return 0

    @admin.action(description='Activate selected departments')
    def activate_departments(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} department(s) activated.', messages.SUCCESS)

    @admin.action(description='Deactivate selected departments')
    def deactivate_departments(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} department(s) deactivated.', messages.WARNING)


# ============================================================
# USER ADMIN
# ============================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = (
        'username', 'full_name_display', 'email', 'employee_number',
        'role', 'department', 'phone_number',
        'is_active', 'is_online', 'account_locked', 'date_joined',
    )
    list_filter = (
        'role', 'department', 'is_active', 'is_staff', 'is_superuser',
        'account_locked', 'is_online', 'gender', 'employment_type',
        'two_factor_enabled', 'date_joined',
    )
    search_fields = (
        'username', 'first_name', 'middle_name', 'last_name',
        'email', 'employee_number', 'national_id', 'phone_number',
        'license_number',
    )
    ordering = ('first_name', 'last_name')
    list_select_related = ('department',)
    list_per_page = 25
    date_hierarchy = 'date_joined'
    filter_horizontal = ('groups', 'user_permissions')

    readonly_fields = (
        'last_login', 'date_joined', 'last_activity', 'login_attempts',
        'password_changed_at', 'updated_at', 'profile_picture_preview',
    )

    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'password')
        }),
        ('Personal Information', {
            'fields': (
                'title', 'first_name', 'middle_name', 'last_name',
                'email', 'national_id', 'date_of_birth', 'gender',
                'profile_picture', 'profile_picture_preview',
            )
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'alternate_phone')
        }),
        ('Professional Information', {
            'fields': (
                'role', 'department', 'employee_number', 'specialization',
                'license_number', 'years_of_experience',
                'emergency_contact_name', 'emergency_contact_phone',
            )
        }),
        ('Employment Details', {
            'fields': (
                'date_joined_organization', 'employment_type', 'created_by',
            )
        }),
        ('Permissions & Status', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
                'account_locked', 'two_factor_enabled', 'two_factor_secret',
            ),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': (
                'receive_email_notifications',
                'receive_sms_notifications',
                'receive_whatsapp_notifications',
            ),
            'classes': ('collapse',)
        }),
        ('Audit & Tracking', {
            'fields': (
                'is_online', 'last_activity', 'last_login',
                'login_attempts', 'password_changed_at', 'updated_at',
                'ip_address', 'user_agent',
            ),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('Authentication', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        ('Personal Information', {
            'classes': ('wide',),
            'fields': ('title', 'first_name', 'middle_name', 'last_name', 'email', 'gender'),
        }),
        ('Professional Information', {
            'classes': ('wide',),
            'fields': ('role', 'department', 'employee_number', 'phone_number'),
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    actions = [
        'activate_users', 'deactivate_users', 'unlock_accounts',
        'reset_login_attempts', 'enable_2fa', 'disable_2fa', 'mark_offline',
    ]

    # ---------- Display Methods ----------

    @admin.display(description='Full Name', ordering='first_name')
    def full_name_display(self, obj):
        return obj.get_full_name() or obj.username

    @admin.display(description='Profile Picture')
    def profile_picture_preview(self, obj):
        if obj and obj.profile_picture:
            return format_html(
                '<img src="{}" style="max-height:150px;max-width:150px;border-radius:8px;" />',
                obj.profile_picture.url,
            )
        return 'No picture uploaded'

    # ---------- Queryset ----------

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department', 'created_by')

    # ---------- Actions ----------

    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated.', messages.SUCCESS)

    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.', messages.WARNING)

    @admin.action(description='Unlock selected accounts')
    def unlock_accounts(self, request, queryset):
        updated = queryset.update(account_locked=False, login_attempts=0)
        self.message_user(request, f'{updated} account(s) unlocked.', messages.SUCCESS)

    @admin.action(description='Reset login attempts')
    def reset_login_attempts(self, request, queryset):
        updated = queryset.update(login_attempts=0)
        self.message_user(
            request, f'Login attempts reset for {updated} user(s).', messages.SUCCESS
        )

    @admin.action(description='Enable 2FA')
    def enable_2fa(self, request, queryset):
        updated = queryset.update(two_factor_enabled=True)
        self.message_user(request, f'2FA enabled for {updated} user(s).', messages.SUCCESS)

    @admin.action(description='Disable 2FA')
    def disable_2fa(self, request, queryset):
        updated = queryset.update(two_factor_enabled=False, two_factor_secret='')
        self.message_user(request, f'2FA disabled for {updated} user(s).', messages.WARNING)

    @admin.action(description='Mark selected users as offline')
    def mark_offline(self, request, queryset):
        updated = queryset.update(is_online=False)
        self.message_user(request, f'{updated} user(s) marked offline.', messages.INFO)

    # ---------- Save Behavior ----------

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ============================================================
# USER SESSION ADMIN
# ============================================================

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'session_key_short', 'ip_address',
        'login_time', 'last_activity', 'logout_time',
        'is_active', 'duration_display',
    )
    list_filter = ('is_active', 'login_time', 'last_activity')
    search_fields = ('user__username', 'user__email', 'session_key', 'ip_address')
    readonly_fields = (
        'user', 'session_key', 'ip_address', 'user_agent',
        'login_time', 'last_activity', 'logout_time', 'is_active',
    )
    list_select_related = ('user',)
    list_per_page = 50
    date_hierarchy = 'login_time'
    ordering = ('-login_time',)

    actions = ['terminate_sessions', 'mark_inactive']

    def has_add_permission(self, request):
        return False

    @admin.display(description='Session Key')
    def session_key_short(self, obj):
        if obj.session_key:
            return obj.session_key[:12] + '...'
        return '— (API)'

    @admin.display(description='Duration')
    def duration_display(self, obj):
        end = obj.logout_time or timezone.now()
        total_seconds = int((end - obj.login_time).total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f'{hours}h {minutes}m'
        if minutes:
            return f'{minutes}m {seconds}s'
        return f'{seconds}s'

    @admin.action(description='Terminate selected sessions')
    def terminate_sessions(self, request, queryset):
        updated = queryset.filter(is_active=True).update(
            is_active=False, logout_time=timezone.now()
        )
        self.message_user(request, f'{updated} session(s) terminated.', messages.SUCCESS)

    @admin.action(description='Mark sessions inactive')
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} session(s) marked inactive.', messages.INFO)


# ============================================================
# AUDIT LOG ADMIN
# ============================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp', 'user', 'action', 'model_name',
        'object_id', 'object_repr_short', 'ip_address',
    )
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user__username', 'model_name', 'object_id', 'object_repr', 'ip_address')
    readonly_fields = (
        'user', 'action', 'model_name', 'object_id', 'object_repr',
        'changes_display', 'ip_address', 'user_agent', 'timestamp',
    )
    list_select_related = ('user',)
    list_per_page = 50
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Object')
    def object_repr_short(self, obj):
        if obj.object_repr:
            return obj.object_repr[:60] + ('...' if len(obj.object_repr) > 60 else '')
        return '—'

    @admin.display(description='Changes')
    def changes_display(self, obj):
        if not obj.changes:
            return '—'
        formatted = json.dumps(obj.changes, indent=2, default=str)
        return format_html(
            '<pre style="max-height:400px;overflow:auto;background:#f8f9fa;'
            'padding:10px;border-radius:4px;">{}</pre>',
            formatted,
        )


# ============================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================

admin.site.site_header = "Hospital Management System"
admin.site.site_title = "HMS Admin"
admin.site.index_title = "Administration Dashboard"