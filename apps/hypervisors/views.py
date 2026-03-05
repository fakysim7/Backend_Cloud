from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Hypervisor
from .serializers import HypervisorSerializer


class HypervisorViewSet(viewsets.ModelViewSet):
    """
    Управление гипервизорами — только для системных администраторов.
    """
    queryset = Hypervisor.objects.all()
    serializer_class = HypervisorSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def available(self, request):
        """Список доступных (online) гипервизоров — для всех авторизованных."""
        qs = Hypervisor.objects.filter(status=Hypervisor.Status.ONLINE)
        return Response(HypervisorSerializer(qs, many=True).data)
