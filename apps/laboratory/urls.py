from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LabTestCategoryViewSet, LabTestViewSet, LabRequestViewSet, LabResultViewSet

router = DefaultRouter()
router.register(r'categories', LabTestCategoryViewSet, basename='labcategory')
router.register(r'tests', LabTestViewSet, basename='labtest')
router.register(r'requests', LabRequestViewSet, basename='labrequest')
router.register(r'results', LabResultViewSet, basename='labresult')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', LabRequestViewSet.as_view({'get': 'dashboard'}), name='lab_dashboard'),
    path('statistics/', LabRequestViewSet.as_view({'get': 'statistics'}), name='lab_statistics'),
]