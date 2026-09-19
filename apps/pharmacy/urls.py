from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MedicationViewSet, PrescriptionViewSet, StockTransactionViewSet,
    pharmacy_prescriptions_page, pharmacy_create_page, pharmacy_detail_page,
    pharmacy_dispensary_page, pharmacy_inventory_page,
)

app_name = 'pharmacy'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'medications', MedicationViewSet, basename='medication')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'transactions', StockTransactionViewSet, basename='stocktransaction')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — before the router so they win on any collision
    # ------------------------------------------------------------
    path('prescriptions/', pharmacy_prescriptions_page, name='pharmacy-prescriptions-page'),
    path('create/', pharmacy_create_page, name='pharmacy-create-page'),
    path('dispensary/', pharmacy_dispensary_page, name='pharmacy-dispensary-page'),
    path('inventory/', pharmacy_inventory_page, name='pharmacy-inventory-page'),
    path('detail/<int:pk>/', pharmacy_detail_page, name='pharmacy-detail-page'),

    # ------------------------------------------------------------
    # DRF API + manual actions
    # ------------------------------------------------------------
    path('', include(router.urls)),
    path('low-stock/', MedicationViewSet.as_view({'get': 'low_stock'}), name='low_stock'),
    path('statistics/', PrescriptionViewSet.as_view({'get': 'statistics'}), name='pharmacy_stats'),
    path('safety-alerts/', PrescriptionViewSet.as_view({'get': 'safety_alerts'}), name='safety_alerts'),
]