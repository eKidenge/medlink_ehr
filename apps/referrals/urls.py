from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReferralViewSet, ReferralNoteViewSet,
    referrals_list_page, referral_create_page,
    referral_detail_page, referral_verify_page,
)

app_name = 'referrals'

# ============================================================
# DRF Router
# ============================================================
router = DefaultRouter()
router.register(r'referrals', ReferralViewSet, basename='referral')
router.register(r'notes', ReferralNoteViewSet, basename='referralnote')

urlpatterns = [
    # ------------------------------------------------------------
    # HTML PAGES — before the router so they win on any collision
    # ------------------------------------------------------------
    path('list/', referrals_list_page, name='referrals-list-page'),
    path('create/', referral_create_page, name='referral-create-page'),
    path('detail/<int:pk>/', referral_detail_page, name='referral-detail-page'),
    path('verify-page/', referral_verify_page, name='referral-verify-page'),

    # ------------------------------------------------------------
    # DRF API + manual action endpoints
    # ------------------------------------------------------------
    path('', include(router.urls)),
    path('verify/', ReferralViewSet.as_view({'get': 'verify'}), name='verify_referral'),
    path('statistics/', ReferralViewSet.as_view({'get': 'statistics'}), name='referral_stats'),
]