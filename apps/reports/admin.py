from django.contrib import admin
from django.utils.html import format_html
from .models import ReportTemplate, ReportJob, AuditReport


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'default_format', 'is_scheduled', 'created_at']
    list_filter = ['report_type', 'is_scheduled', 'is_public']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'report_type', 'description')
        }),
        ('Configuration', {
            'fields': ('query_config', 'columns', 'filters', 'default_format')
        }),
        ('Scheduling', {
            'fields': ('is_scheduled', 'schedule_frequency', 'last_run', 'next_run'),
            'classes': ('collapse',)
        }),
        ('Sharing', {
            'fields': ('is_public', 'shared_with'),
            'classes': ('collapse',)
        })
    )


@admin.register(ReportJob)
class ReportJobAdmin(admin.ModelAdmin):
    list_display = ['template', 'requested_by', 'status_coloured', 'output_format', 'created_at', 'completed_at']
    list_filter = ['status', 'output_format', 'created_at']
    search_fields = ['template__name', 'requested_by__username']
    readonly_fields = ['created_at', 'completed_at']
    raw_id_fields = ['template', 'requested_by']
    
    def status_coloured(self, obj):
        colours = {
            'pending': '#FF9800',
            'processing': '#2196F3',
            'completed': '#4CAF50',
            'failed': '#F44336'
        }
        colour = colours.get(obj.status, '#9E9E9E')
        return format_html('<span style="color: {};">{}</span>', colour, obj.status.upper())
    status_coloured.short_description = 'Status'


@admin.register(AuditReport)
class AuditReportAdmin(admin.ModelAdmin):
    list_display = ['report_number', 'action_type', 'date_from', 'date_to', 'total_events', 'generated_by', 'generated_at']
    list_filter = ['action_type', 'generated_at']
    search_fields = ['report_number']
    readonly_fields = ['report_number', 'generated_at']
    raw_id_fields = ['generated_by']