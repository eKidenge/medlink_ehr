from django.contrib import admin
from .models import DashboardWidget, UserDashboard, UserDashboardWidget, Notification


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'widget_type', 'width', 'height', 'order', 'is_visible']
    list_filter = ['widget_type', 'is_visible']
    search_fields = ['name']
    list_editable = ['width', 'height', 'order', 'is_visible']


@admin.register(UserDashboard)
class UserDashboardAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'created_at']
    list_filter = ['theme', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    raw_id_fields = ['recipient']
    
    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset()
        return super().get_queryset().filter(recipient=request.user)