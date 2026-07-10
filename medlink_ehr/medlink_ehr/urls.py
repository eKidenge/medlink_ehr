"""
URL configuration for medlink_ehr project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.views import LoginView, LogoutView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect

# Schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="MedLink EHR API",
        default_version='v1',
        description="Electronic Health Record System for Kenyan Healthcare Facilities",
        terms_of_service="https://www.medlink.co.ke/terms/",
        contact=openapi.Contact(email="support@medlink.co.ke"),
        license=openapi.License(name="Proprietary License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Custom logout view that accepts GET requests
def custom_logout(request):
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect('/login/')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # Authentication URLs
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', custom_logout, name='logout'),  # Changed to custom logout
    path('register/', TemplateView.as_view(template_name='register.html'), name='register'),
    
    # JWT Authentication API
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Home page - Landing page
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Dashboard HTML - includes all role-based dashboard routes
    path('dashboard/', include('apps.dashboard.urls')),
    
    # App URLs (HTML views)
    path('accounts/', include('apps.accounts.urls')),
    path('patients/', include('apps.patients.urls')),
    path('visits/', include('apps.visits.urls')),
    path('triage/', include('apps.triage.urls')),
    path('admissions/', include('apps.admissions.urls')),
    path('laboratory/', include('apps.laboratory.urls')),
    path('pharmacy/', include('apps.pharmacy.urls')),
    path('referrals/', include('apps.referrals.urls')),
    path('reports/', include('apps.reports.urls')),
    
    # API URLs (all under /api/ prefix)
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/patients/', include('apps.patients.urls')),
    path('api/visits/', include('apps.visits.urls')),
    path('api/triage/', include('apps.triage.urls')),
    path('api/admissions/', include('apps.admissions.urls')),
    path('api/laboratory/', include('apps.laboratory.urls')),
    path('api/pharmacy/', include('apps.pharmacy.urls')),
    path('api/referrals/', include('apps.referrals.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar (only in development)
    try:
        import debug_toolbar
        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

# Custom error handlers
handler400 = 'apps.dashboard.views.handler400'
handler403 = 'apps.dashboard.views.handler403'
handler404 = 'apps.dashboard.views.handler404'
handler500 = 'apps.dashboard.views.handler500'