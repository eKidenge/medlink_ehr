from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, DepartmentViewSet, AuthViewSet, AuditLogViewSet,
    users_page, departments_page, profile_page, settings_page, audit_page,
)

app_name = 'accounts'

# ============================================================
# DRF Router — registered at root so it works with BOTH
# /accounts/* (HTML) and /api/accounts/* (API) mounts
# in the project urls.py
# ============================================================
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — unique paths so they never shadow the DRF routes
    # Rendered when this file is included at /accounts/ in project urls.py
    # ------------------------------------------------------------
    path('users-page/', users_page, name='users-page'),
    path('departments-page/', departments_page, name='departments-page'),
    path('profile-page/', profile_page, name='profile-page'),
    path('settings-page/', settings_page, name='settings-page'),
    path('audit-page/', audit_page, name='audit-page'),

    # ------------------------------------------------------------
    # DRF API
    # Rendered at /accounts/* AND /api/accounts/*
    # ------------------------------------------------------------
    path('', include(router.urls)),
    path('profile/', UserViewSet.as_view({'get': 'me', 'put': 'update_me'}), name='api-profile'),
    path('settings/', AuthViewSet.as_view({'post': 'change_password'}), name='api-change-password'),
]