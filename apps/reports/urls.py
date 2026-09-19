from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReportTemplateViewSet, ReportJobViewSet, AuditReportViewSet,
    reports_index_page, reports_generate_page,
    reports_templates_page, reports_view_page,
)

app_name = 'reports'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'templates', ReportTemplateViewSet, basename='reporttemplate')
router.register(r'jobs', ReportJobViewSet, basename='reportjob')
router.register(r'audit', AuditReportViewSet, basename='auditreport')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — must come before the router include
    # ------------------------------------------------------------
    path('', reports_index_page, name='reports-index-page'),
    path('generate/', reports_generate_page, name='reports-generate-page'),
    path('templates-html/', reports_templates_page, name='reports-templates-page'),
    path('view/', reports_view_page, name='reports-view-page'),
    path('view/<int:job_id>/', reports_view_page, name='reports-view-detail-page'),

    # ------------------------------------------------------------
    # DRF API
    # ------------------------------------------------------------
    path('', include(router.urls)),
]