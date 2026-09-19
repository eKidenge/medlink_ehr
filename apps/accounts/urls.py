from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, DepartmentViewSet, AuthViewSet, AuditLogViewSet,
    users_page, departments_page, profile_page, settings_page, audit_page,
)

app_name = 'accounts'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    # HTML PAGES — at /accounts/*  (no conflict with API)
    path('users/', users_page, name='users-page'),
    path('departments/', departments_page, name='departments-page'),
    path('profile-page/', profile_page, name='profile-page'),
    path('settings-page/', settings_page, name='settings-page'),
    path('audit/', audit_page, name='audit-page'),

    # DRF API — at /api/accounts/*
    path('api/', include(router.urls)),
    path('api/profile/', UserViewSet.as_view({'get': 'me', 'put': 'update_me'}), name='api-profile'),
    path('api/settings/', AuthViewSet.as_view({'post': 'change_password'}), name='api-change-password'),
]