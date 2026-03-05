"""
Celery-задачи для асинхронного управления жизненным циклом VM.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def create_vm_task(self, vm_id: str):
    """Создаёт VM на гипервизоре через libvirt."""
    from django.conf import settings
    from apps.virtual_machines.models import VirtualMachine
    from apps.virtual_machines.services.libvirt_service import LibvirtService
    from apps.virtual_machines.services.quota_service import QuotaService

    try:
        vm = VirtualMachine.objects.select_related(
            'hypervisor', 'organization'
        ).get(id=vm_id)

        vm.status = VirtualMachine.Status.CREATING
        vm.save(update_fields=['status', 'updated_at'])

        with LibvirtService(vm.hypervisor.host, vm.hypervisor.port) as svc:
            libvirt_uuid = svc.create_vm(
                name=f"vm-{str(vm.id)[:8]}",
                vcpus=vm.vcpus,
                ram_mb=vm.ram_mb,
                disk_gb=vm.disk_gb,
                os_type=vm.os_type,
                disk_base_path=settings.LIBVIRT_DISK_PATH,
            )

        vm.libvirt_uuid = libvirt_uuid
        vm.status = VirtualMachine.Status.RUNNING
        vm.error_message = ''
        vm.save(update_fields=['libvirt_uuid', 'status', 'error_message', 'updated_at'])
        logger.info(f"VM {vm.id} created successfully")

    except Exception as exc:
        logger.exception(f"Failed to create VM {vm_id}: {exc}")
        try:
            vm = VirtualMachine.objects.select_related('organization').get(id=vm_id)
            # Вернуть квоту
            QuotaService.release(vm.organization, vm.vcpus, vm.ram_mb, vm.disk_gb)
            vm.status = VirtualMachine.Status.ERROR
            vm.error_message = str(exc)
            vm.save(update_fields=['status', 'error_message', 'updated_at'])
        except Exception as inner:
            logger.exception(f"Failed to rollback VM {vm_id}: {inner}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def delete_vm_task(self, vm_id: str):
    """Удаляет VM с гипервизора и освобождает квоту."""
    from django.conf import settings
    from apps.virtual_machines.models import VirtualMachine
    from apps.virtual_machines.services.libvirt_service import LibvirtService
    from apps.virtual_machines.services.quota_service import QuotaService

    try:
        vm = VirtualMachine.objects.select_related(
            'hypervisor', 'organization'
        ).get(id=vm_id)

        if vm.libvirt_uuid and vm.hypervisor:
            disk_path = f"{settings.LIBVIRT_DISK_PATH}/{vm.libvirt_uuid}.qcow2"
            with LibvirtService(vm.hypervisor.host, vm.hypervisor.port) as svc:
                svc.delete_vm(str(vm.libvirt_uuid), disk_path)

        QuotaService.release(vm.organization, vm.vcpus, vm.ram_mb, vm.disk_gb)

        vm.status = VirtualMachine.Status.DELETED
        vm.deleted_at = timezone.now()
        vm.save(update_fields=['status', 'deleted_at', 'updated_at'])
        logger.info(f"VM {vm.id} deleted successfully")

    except Exception as exc:
        logger.exception(f"Failed to delete VM {vm_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def start_vm_task(self, vm_id: str):
    """Запускает остановленную VM."""
    from apps.virtual_machines.models import VirtualMachine
    from apps.virtual_machines.services.libvirt_service import LibvirtService
    try:
        vm = VirtualMachine.objects.select_related('hypervisor').get(id=vm_id)
        with LibvirtService(vm.hypervisor.host, vm.hypervisor.port) as svc:
            svc.start_vm(str(vm.libvirt_uuid))
        vm.status = VirtualMachine.Status.RUNNING
        vm.error_message = ''
        vm.save(update_fields=['status', 'error_message', 'updated_at'])
    except Exception as exc:
        logger.exception(f"Failed to start VM {vm_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def stop_vm_task(self, vm_id: str):
    """Останавливает VM (graceful shutdown)."""
    from apps.virtual_machines.models import VirtualMachine
    from apps.virtual_machines.services.libvirt_service import LibvirtService
    try:
        vm = VirtualMachine.objects.select_related('hypervisor').get(id=vm_id)
        with LibvirtService(vm.hypervisor.host, vm.hypervisor.port) as svc:
            svc.stop_vm(str(vm.libvirt_uuid))
        vm.status = VirtualMachine.Status.STOPPED
        vm.save(update_fields=['status', 'updated_at'])
    except Exception as exc:
        logger.exception(f"Failed to stop VM {vm_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def reboot_vm_task(self, vm_id: str):
    """Перезапускает VM."""
    from apps.virtual_machines.models import VirtualMachine
    from apps.virtual_machines.services.libvirt_service import LibvirtService
    try:
        vm = VirtualMachine.objects.select_related('hypervisor').get(id=vm_id)
        vm.status = VirtualMachine.Status.RESTARTING
        vm.save(update_fields=['status', 'updated_at'])
        with LibvirtService(vm.hypervisor.host, vm.hypervisor.port) as svc:
            svc.reboot_vm(str(vm.libvirt_uuid))
        vm.status = VirtualMachine.Status.RUNNING
        vm.save(update_fields=['status', 'updated_at'])
    except Exception as exc:
        logger.exception(f"Failed to reboot VM {vm_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def sync_vm_statuses():
    """Периодически синхронизирует статусы VM с гипервизором (Celery Beat)."""
    from apps.virtual_machines.models import VirtualMachine
    from apps.virtual_machines.services.libvirt_service import LibvirtService

    active_vms = VirtualMachine.objects.filter(
        status__in=[VirtualMachine.Status.RUNNING, VirtualMachine.Status.STOPPED],
        libvirt_uuid__isnull=False,
        hypervisor__isnull=False,
    ).select_related('hypervisor')

    updated = 0
    for vm in active_vms:
        try:
            with LibvirtService(vm.hypervisor.host, vm.hypervisor.port) as svc:
                real_status = svc.get_vm_status(str(vm.libvirt_uuid))
            if real_status != vm.status and real_status != 'unknown':
                vm.status = real_status
                vm.save(update_fields=['status', 'updated_at'])
                updated += 1
        except Exception as e:
            logger.warning(f"Cannot sync VM {vm.id}: {e}")

    logger.info(f"VM sync complete: {updated} updated out of {active_vms.count()}")
