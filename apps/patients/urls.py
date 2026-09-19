from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PatientViewSet,
    patients_list_page, patient_create_page, patient_detail_page,
    patient_edit_page, patient_merge_page, patient_qr_page,
)

app_name = 'patients'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — before the router so they win on any collision
    # ------------------------------------------------------------
    path('list/', patients_list_page, name='patients-list-page'),
    path('create/', patient_create_page, name='patient-create-page'),
    path('merge/', patient_merge_page, name='patient-merge-page'),
    path('<int:pk>/edit/', patient_edit_page, name='patient-edit-page'),
    path('<int:pk>/qr/', patient_qr_page, name='patient-qr-page'),
    path('<int:pk>/', patient_detail_page, name='patient-detail-page'),

    # ------------------------------------------------------------
    # DRF API — everything else
    # ------------------------------------------------------------
    path('', include(router.urls)),
]