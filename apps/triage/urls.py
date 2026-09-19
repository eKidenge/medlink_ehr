from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TriageViewSet, TriageQueueViewSet,
    triage_list_page, triage_waiting_page, triage_queue_page, triage_assessment_page,
)

app_name = 'triage'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'triage', TriageViewSet, basename='triage')
router.register(r'queue', TriageQueueViewSet, basename='triagequeue')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — before the router
    # ------------------------------------------------------------
    path('list/', triage_list_page, name='triage-list-page'),
    path('waiting/', triage_waiting_page, name='triage-waiting-page'),
    path('queue/', triage_queue_page, name='triage-queue-page'),
    path('assessment/<int:pk>/', triage_assessment_page, name='triage-assessment-page'),

    # ------------------------------------------------------------
    # DRF API
    # ------------------------------------------------------------
    path('', include(router.urls)),
    path('start/', TriageViewSet.as_view({'post': 'start_triage'}), name='start_triage'),
]