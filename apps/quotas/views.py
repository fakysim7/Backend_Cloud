from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import ResourceQuota
from .serializers import ResourceQuotaSerializer
from core.permissions import IsOrganizationMember


class QuotaDetailView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/quota/  — текущие квоты и использование (любой участник)
    PATCH /api/quota/ — изменить лимиты (только superuser/admin системы)
    """
    serializer_class = ResourceQuotaSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT'):
            return [IsAdminUser()]
        return [IsAuthenticated(), IsOrganizationMember()]

    def get_object(self):
        return ResourceQuota.objects.get(
            organization=self.request.current_organization
        )
