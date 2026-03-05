"""
Сервис квот — атомарный контроль ресурсов организации.
Все операции выполняются внутри SELECT FOR UPDATE транзакции.
"""
import logging
from django.db import transaction
from apps.accounts.models import Organization
from apps.quotas.models import ResourceQuota
from core.exceptions import QuotaExceededError

logger = logging.getLogger(__name__)


class QuotaService:

    @staticmethod
    def check_and_allocate(
        organization: Organization,
        vcpus: int,
        ram_mb: int,
        disk_gb: int,
    ) -> None:
        """
        Атомарно проверяет квоту и резервирует ресурсы.
        Выбрасывает QuotaExceededError если хоть один лимит превышен.
        """
        with transaction.atomic():
            quota = ResourceQuota.objects.select_for_update().get(
                organization=organization
            )
            errors = []

            if not quota.check_vcpu(vcpus):
                available = quota.max_vcpus - quota.used_vcpus
                errors.append(
                    f"vCPU: запрошено {vcpus}, доступно {available} из {quota.max_vcpus}"
                )
            if not quota.check_ram(ram_mb):
                available_mb = quota.max_ram_mb - quota.used_ram_mb
                errors.append(
                    f"RAM: запрошено {ram_mb}MB, доступно {available_mb}MB из {quota.max_ram_mb}MB"
                )
            if not quota.check_disk(disk_gb):
                available_gb = quota.max_disk_gb - quota.used_disk_gb
                errors.append(
                    f"Диск: запрошено {disk_gb}GB, доступно {available_gb}GB из {quota.max_disk_gb}GB"
                )
            if not quota.check_vm_count():
                errors.append(f"Достигнут лимит VM: максимум {quota.max_vms} VM")

            if errors:
                logger.warning(
                    f"Quota exceeded for org={organization.slug}: {errors}"
                )
                raise QuotaExceededError(errors)

            quota.allocate(vcpus, ram_mb, disk_gb)
            logger.info(
                f"Allocated vcpu={vcpus} ram={ram_mb}MB disk={disk_gb}GB "
                f"for org={organization.slug}"
            )

    @staticmethod
    def release(
        organization: Organization,
        vcpus: int,
        ram_mb: int,
        disk_gb: int,
    ) -> None:
        """Атомарно освобождает ресурсы при удалении VM."""
        with transaction.atomic():
            quota = ResourceQuota.objects.select_for_update().get(
                organization=organization
            )
            quota.release(vcpus, ram_mb, disk_gb)
            logger.info(
                f"Released vcpu={vcpus} ram={ram_mb}MB disk={disk_gb}GB "
                f"for org={organization.slug}"
            )
