from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WardViewSet, BedViewSet, AdmissionViewSet, DailyRoundViewSet

router = DefaultRouter()
router.register(r'wards', WardViewSet, basename='ward')
router.register(r'beds', BedViewSet, basename='bed')
router.register(r'admissions', AdmissionViewSet, basename='admission')
router.register(r'rounds', DailyRoundViewSet, basename='round')

urlpatterns = [
    path('', include(router.urls)),
    path('census/', AdmissionViewSet.as_view({'get': 'census'}), name='census'),
    path('statistics/', AdmissionViewSet.as_view({'get': 'statistics'}), name='admission_stats'),
]