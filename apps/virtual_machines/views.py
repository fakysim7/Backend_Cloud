import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsOrganizationMember, IsOrganizationAdmin
from core.exceptions import QuotaExceededError, HypervisorUnavailableError, VMOperationError

from .models import VirtualMachine
from .serializers import (
    VirtualMachineSerializer,
    VirtualMachineCreateSerializer,
    VirtualMachineListSerializer,
)
from apps.accounts.models import Organization
from .filters import VirtualMachineFilter
from .scheduler import select_best_hypervisor
from .services.quota_service import QuotaService
from .tasks import (
    create_vm_task, delete_vm_task,
    start_vm_task, stop_vm_task, reboot_vm_task,
)

logger = logging.getLogger(__name__)

# Переходы статусов: какие операции разрешены из каких состояний
ALLOWED_TRANSITIONS = {
    'start':  [VirtualMachine.Status.STOPPED],
    'stop':   [VirtualMachine.Status.RUNNING],
    'reboot': [VirtualMachine.Status.RUNNING],
}


class VirtualMachineViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления виртуальными машинами.

    Все запросы требуют заголовок: X-Organization-Slug: <slug>
    Пользователь видит только VM своей организации.
    """
    filterset_class = VirtualMachineFilter
    search_fields   = ['name', 'ip_address', 'description']
    ordering_fields = ['created_at', 'name', 'vcpus', 'ram_mb', 'status']
    ordering        = ['-created_at']

    def get_permissions(self):
        if self.action in ['destroy', 'create']:
            return [IsAuthenticated(), IsOrganizationMember()]
        return [IsAuthenticated(), IsOrganizationMember()]

    def get_queryset(self):
        org = self.request.current_organization
        if not org:
            return VirtualMachine.objects.none()
        return (
            VirtualMachine.objects
            .filter(organization=org)
            .exclude(status=VirtualMachine.Status.DELETED)
            .select_related('hypervisor', 'created_by', 'organization')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return VirtualMachineCreateSerializer
        if self.action == 'list':
            return VirtualMachineListSerializer
        return VirtualMachineSerializer

    # ── CREATE ─────────────────────────────────────────────────────

    def create(self, request, *args, **kwargs):
        org = request.current_organization
        if not org:
            return Response(
                {'error': 'Укажите заголовок X-Organization-Slug.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VirtualMachineCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 1. Выбрать гипервизор
        hypervisor = select_best_hypervisor(data['vcpus'], data['ram_mb'], data['disk_gb'])
        if not hypervisor:
            raise HypervisorUnavailableError(
                'Нет доступных гипервизоров с достаточными ресурсами.'
            )

        # 2. Проверить и зарезервировать квоту (атомарно)
        QuotaService.check_and_allocate(org, data['vcpus'], data['ram_mb'], data['disk_gb'])

        # 3. Создать запись в БД
        if not data.get('organization'):
            personal_org, created = Organization.objects.get_or_create(
                name=f"Личные ВМ {request.user.email}",
                slug=f"user-{str(request.user.id).split('-')[0]}",
                defaults={
                    'description': f'Личная организация {request.user.email}'


                    
                }
            )
            data['organization'] = personal_org
            data['created_by'] = request.user

        vm = VirtualMachine.objects.create(
            organization=data['organization'],  # ← Теперь всегда есть
            created_by=request.user,
            hypervisor=hypervisor,
            **data,
        )

        # 4. Запустить асинхронную задачу создания VM
        create_vm_task.delay(str(vm.id))

        logger.info(
            f"VM creation initiated: {vm.id} org={org.slug} "
            f"vcpu={vm.vcpus} ram={vm.ram_mb} disk={vm.disk_gb}"
        )
        return Response(
            VirtualMachineSerializer(vm).data,
            status=status.HTTP_202_ACCEPTED,
        )

    # ── DELETE ─────────────────────────────────────────────────────

    def destroy(self, request, *args, **kwargs):
        vm = self.get_object()
        if not vm.is_actionable:
            raise VMOperationError(
                f'Нельзя удалить VM в статусе "{vm.get_status_display()}".'
            )
        delete_vm_task.delay(str(vm.id))
        return Response(status=status.HTTP_202_ACCEPTED)

    # ── UPDATE — только имя и описание ────────────────────────────

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        vm = self.get_object()
        allowed_fields = {'name', 'description'}
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        serializer = VirtualMachineSerializer(vm, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    # ── ACTIONS ────────────────────────────────────────────────────

    def _vm_action(self, request, task_fn, allowed_statuses: list, action_name: str):
        vm = self.get_object()
        if vm.status not in allowed_statuses:
            raise VMOperationError(
                f'Операция "{action_name}" недоступна для VM в статусе "{vm.get_status_display()}".'
            )
        task_fn.delay(str(vm.id))
        return Response({'status': 'accepted', 'vm_id': str(vm.id)})

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Запустить остановленную VM."""
        return self._vm_action(request, start_vm_task, [VirtualMachine.Status.STOPPED], 'start')

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Остановить запущенную VM."""
        return self._vm_action(request, stop_vm_task, [VirtualMachine.Status.RUNNING], 'stop')

    @action(detail=True, methods=['post'])
    def reboot(self, request, pk=None):
        """Перезапустить VM."""
        return self._vm_action(request, reboot_vm_task, [VirtualMachine.Status.RUNNING], 'reboot')

    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """Получить актуальный статус VM (из libvirt, не из БД)."""
        from .services.libvirt_service import LibvirtService
        vm = self.get_object()
        if not vm.libvirt_uuid or not vm.hypervisor:
            return Response({'status': vm.status, 'source': 'db'})
        try:
            with LibvirtService(vm.hypervisor.host, vm.hypervisor.port) as svc:
                real_status = svc.get_vm_status(str(vm.libvirt_uuid))
            return Response({'status': real_status, 'source': 'hypervisor'})
        except Exception as e:
            return Response({'status': vm.status, 'source': 'db', 'error': str(e)})
