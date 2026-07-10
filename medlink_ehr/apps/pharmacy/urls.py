from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicationViewSet, PrescriptionViewSet, StockTransactionViewSet

router = DefaultRouter()
router.register(r'medications', MedicationViewSet, basename='medication')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'transactions', StockTransactionViewSet, basename='stocktransaction')

urlpatterns = [
    path('', include(router.urls)),
    path('low-stock/', MedicationViewSet.as_view({'get': 'low_stock'}), name='low_stock'),
    path('statistics/', PrescriptionViewSet.as_view({'get': 'statistics'}), name='pharmacy_stats'),
    path('safety-alerts/', PrescriptionViewSet.as_view({'get': 'safety_alerts'}), name='safety_alerts'),
]