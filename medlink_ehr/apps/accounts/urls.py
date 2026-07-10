from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, DepartmentViewSet, AuthViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    path('', include(router.urls)),
    path('profile/', UserViewSet.as_view({'get': 'me', 'put': 'update_me'}), name='profile'),
    path('settings/', AuthViewSet.as_view({'post': 'change_password'}), name='change_password'),
]