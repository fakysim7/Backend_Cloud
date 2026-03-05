import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def sync_hypervisor_resources():
    """Обновляет used_* на гипервизорах из реальных данных libvirt."""
    from apps.hypervisors.models import Hypervisor
    from apps.virtual_machines.services.libvirt_service import LibvirtService

    for hypervisor in Hypervisor.objects.filter(status=Hypervisor.Status.ONLINE):
        try:
            with LibvirtService(hypervisor.host, hypervisor.port) as svc:
                stats = svc.get_node_stats()
            hypervisor.used_vcpus = stats['used_vcpus']
            hypervisor.used_ram_mb = stats['used_ram_mb']
            hypervisor.last_heartbeat = timezone.now()
            hypervisor.save(update_fields=['used_vcpus', 'used_ram_mb', 'last_heartbeat', 'updated_at'])
        except Exception as e:
            logger.warning(f"Hypervisor {hypervisor.name} heartbeat failed: {e}")
            hypervisor.status = Hypervisor.Status.OFFLINE
            hypervisor.save(update_fields=['status', 'updated_at'])
