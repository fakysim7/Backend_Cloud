from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VirtualMachineViewSet

router = DefaultRouter()
router.register('vms', VirtualMachineViewSet, basename='vm')

urlpatterns = [path('', include(router.urls))]
