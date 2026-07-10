from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReferralViewSet, ReferralNoteViewSet

router = DefaultRouter()
router.register(r'referrals', ReferralViewSet, basename='referral')
router.register(r'notes', ReferralNoteViewSet, basename='referralnote')

urlpatterns = [
    path('', include(router.urls)),
    path('verify/', ReferralViewSet.as_view({'get': 'verify'}), name='verify_referral'),
    path('statistics/', ReferralViewSet.as_view({'get': 'statistics'}), name='referral_stats'),
]