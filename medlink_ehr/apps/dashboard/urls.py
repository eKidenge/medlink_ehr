from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from .views import DashboardViewSet, NotificationViewSet
from django.contrib.auth.decorators import login_required

# API Router - for API endpoints only
router = DefaultRouter()
router.register(r'api', DashboardViewSet, basename='dashboard')
router.register(r'api/notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # ============================================================
    # HTML DASHBOARD VIEWS (for actual web pages)
    # ============================================================
    
    # Role-based Dashboard HTML Views
    path('admin/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='admin_dashboard'),
    path('doctor/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='doctor_dashboard'),
    path('nurse/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='nurse_dashboard'),
    path('lab/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='lab_dashboard'),
    path('pharmacy/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='pharmacy_dashboard'),
    path('reception/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='reception_dashboard'),
    path('cashier/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='cashier_dashboard'),
    path('manager/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='manager_dashboard'),
    path('records/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='records_dashboard'),
    path('viewer/', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='viewer_dashboard'),
    
    # Default dashboard redirect (checks user role and redirects to correct dashboard)
    path('', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='dashboard'),
    
    # ============================================================
    # API ENDPOINTS (for AJAX/JavaScript data fetching)
    # ============================================================
    
    # API endpoints via router (all under /api/)
    path('', include(router.urls)),
    
    # Additional direct API endpoints
    path('api/widgets/', DashboardViewSet.as_view({'get': 'widgets'}), name='widgets'),
    path('api/stats/', DashboardViewSet.as_view({'get': 'stats'}), name='stats'),
    path('api/kpis/', DashboardViewSet.as_view({'get': 'kpis'}), name='kpis'),
    path('api/activity/', DashboardViewSet.as_view({'get': 'activity_feed'}), name='activity'),
    path('api/my-dashboard/', DashboardViewSet.as_view({'get': 'my_dashboard'}), name='my_dashboard'),
    path('api/update-layout/', DashboardViewSet.as_view({'post': 'update_layout'}), name='update_layout'),
    path('api/my-patients/', DashboardViewSet.as_view({'get': 'my_patients'}), name='my_patients'),
    path('api/my-appointments/', DashboardViewSet.as_view({'get': 'my_appointments'}), name='my_appointments'),
    path('api/triage-queue/', DashboardViewSet.as_view({'get': 'triage_queue'}), name='triage_queue'),
    path('api/pending-lab-results/', DashboardViewSet.as_view({'get': 'pending_lab_results'}), name='pending_lab_results'),
    
    # ============================================================
    # NOTIFICATION API ENDPOINTS (ADD THIS SECTION)
    # ============================================================
    path('api/notifications/unread/', NotificationViewSet.as_view({'get': 'unread'}), name='unread_notifications'),
    path('api/notifications/<int:pk>/mark_read/', NotificationViewSet.as_view({'post': 'mark_read'}), name='mark_read_notification'),
    path('api/notifications/mark_all_read/', NotificationViewSet.as_view({'post': 'mark_all_read'}), name='mark_all_read_notifications'),
]