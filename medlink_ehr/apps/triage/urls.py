from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TriageViewSet, TriageQueueViewSet

router = DefaultRouter()
router.register(r'triage', TriageViewSet, basename='triage')
router.register(r'queue', TriageQueueViewSet, basename='triagequeue')

urlpatterns = [
    path('', include(router.urls)),
    path('waiting/', TriageViewSet.as_view({'get': 'waiting_list'}), name='waiting_list'),
    path('start/', TriageViewSet.as_view({'post': 'start_triage'}), name='start_triage'),
]