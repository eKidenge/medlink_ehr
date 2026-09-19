from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LabTestCategoryViewSet, LabTestViewSet, LabRequestViewSet, LabResultViewSet,
    lab_requests_page, lab_create_page, lab_detail_page,
    lab_processing_page, lab_results_page,
)

app_name = 'laboratory'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'categories', LabTestCategoryViewSet, basename='labcategory')
router.register(r'tests', LabTestViewSet, basename='labtest')
router.register(r'requests', LabRequestViewSet, basename='labrequest')
router.register(r'results', LabResultViewSet, basename='labresult')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — before the router so they win on any URL collision
    # ------------------------------------------------------------
    path('requests/', lab_requests_page, name='lab-requests-page'),
    path('create/', lab_create_page, name='lab-create-page'),
    path('processing/', lab_processing_page, name='lab-processing-page'),
    path('results/', lab_results_page, name='lab-results-page'),
    path('results/<int:pk>/', lab_results_page, name='lab-results-detail-page'),
    path('detail/<int:pk>/', lab_detail_page, name='lab-detail-page'),

    # ------------------------------------------------------------
    # DRF API + existing action endpoints
    # ------------------------------------------------------------
    path('', include(router.urls)),
    path('dashboard/', LabRequestViewSet.as_view({'get': 'dashboard'}), name='lab_dashboard'),
    path('statistics/', LabRequestViewSet.as_view({'get': 'statistics'}), name='lab_statistics'),
]