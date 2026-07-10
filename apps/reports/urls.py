from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportTemplateViewSet, ReportJobViewSet, AuditReportViewSet

router = DefaultRouter()
router.register(r'templates', ReportTemplateViewSet, basename='reporttemplate')
router.register(r'jobs', ReportJobViewSet, basename='reportjob')
router.register(r'audit', AuditReportViewSet, basename='auditreport')

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', ReportTemplateViewSet.as_view({'post': 'generate'}), name='generate_report'),
    path('download/<int:job_id>/', ReportJobViewSet.as_view({'get': 'download'}), name='download_report'),
]