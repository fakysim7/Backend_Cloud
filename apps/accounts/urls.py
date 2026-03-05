from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (RegisterView, MeView, OrganizationViewSet,
    ClientViewSet, PlanViewSet, OrganizationSubscriptionViewSet )

router = DefaultRouter()
router.register('organizations', OrganizationViewSet, basename='organization')
router.register(r'clients', ClientViewSet)
router.register(r'plans', PlanViewSet) 
router.register(r'subscriptions', OrganizationSubscriptionViewSet)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),
]
