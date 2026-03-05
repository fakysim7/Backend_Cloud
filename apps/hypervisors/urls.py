from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HypervisorViewSet

router = DefaultRouter()
router.register('hypervisors', HypervisorViewSet, basename='hypervisor')

urlpatterns = [path('', include(router.urls))]
