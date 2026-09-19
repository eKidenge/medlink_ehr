from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VisitViewSet,
    visits_list_page, visit_check_in_page, visit_create_page,
    visit_detail_page, visit_queue_page,
)

app_name = 'visits'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'visits', VisitViewSet, basename='visit')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — before the router
    # ------------------------------------------------------------
    path('list/', visits_list_page, name='visits-list-page'),
    path('check_in/', visit_check_in_page, name='visit-check-in-page'),
    path('create/', visit_create_page, name='visit-create-page'),
    path('queue/', visit_queue_page, name='visit-queue-page'),
    path('detail/<int:pk>/', visit_detail_page, name='visit-detail-page'),

    # ------------------------------------------------------------
    # DRF API
    # ------------------------------------------------------------
    path('', include(router.urls)),
]