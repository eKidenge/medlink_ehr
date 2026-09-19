from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WardViewSet, BedViewSet, AdmissionViewSet, DailyRoundViewSet,
    admissions_list_page, admission_create_page, admission_detail_page,
    admissions_wards_page, admissions_beds_page, admissions_rounds_page,
)

app_name = 'admissions'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'wards', WardViewSet, basename='ward')
router.register(r'beds', BedViewSet, basename='bed')
router.register(r'admissions', AdmissionViewSet, basename='admission')
router.register(r'rounds', DailyRoundViewSet, basename='round')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — before the router so they win on any collision
    # ------------------------------------------------------------
    path('list/', admissions_list_page, name='admissions-list-page'),
    path('create/', admission_create_page, name='admission-create-page'),
    path('detail/<int:pk>/', admission_detail_page, name='admission-detail-page'),
    path('wards-page/', admissions_wards_page, name='admissions-wards-page'),
    path('beds-page/', admissions_beds_page, name='admissions-beds-page'),
    path('rounds-page/', admissions_rounds_page, name='admissions-rounds-page'),

    # ------------------------------------------------------------
    # DRF API
    # ------------------------------------------------------------
    path('', include(router.urls)),
    path('census/', AdmissionViewSet.as_view({'get': 'census'}), name='census'),
    path('statistics/', AdmissionViewSet.as_view({'get': 'statistics'}), name='admission_stats'),
]