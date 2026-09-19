from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from .views import DashboardViewSet, NotificationViewSet
from django.contrib.auth.decorators import login_required

# ============================================================
# API Router — no 'api/' prefix here.
# This file is mounted at '/api/dashboard/' in project urls.py,
# so registering r'' gives us /api/dashboard/stats/, /api/dashboard/kpis/,
# and r'notifications' gives /api/dashboard/notifications/unread/, etc.
# ============================================================
router = DefaultRouter()
router.register(r'', DashboardViewSet, basename='dashboard')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # ============================================================
    # HTML DASHBOARD VIEWS (actual web pages, no /api prefix)
    # These are served when this file is included at '/dashboard/'
    # in project urls.py — the actual URLs are /dashboard/admin/,
    # /dashboard/doctor/, etc.
    # ============================================================
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

    # Default dashboard — served at /dashboard/ and /api/dashboard/
    path('', DashboardViewSet.as_view({'get': 'dashboard_html'}), name='dashboard'),

    # ============================================================
    # API ENDPOINTS — handled by the router above
    # The router generates: /api/dashboard/stats/, /api/dashboard/kpis/,
    # /api/dashboard/activity_feed/, /api/dashboard/notifications/unread/, etc.
    # ============================================================
    path('', include(router.urls)),
]