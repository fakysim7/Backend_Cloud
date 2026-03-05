from django.db import models
from django.core.validators import MinValueValidator
from apps.accounts.models import Organization


class ResourceQuota(models.Model):
    """
    Квота ресурсов на организацию.
    Все операции с полями used_* должны быть атомарными (через QuotaService).
    """
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE,
        related_name='quota', verbose_name='Организация'
    )

    # ── CPU ────────────────────────────────
    max_vcpus = models.PositiveIntegerField(
        default=10, validators=[MinValueValidator(1)],
        verbose_name='Макс. vCPU'
    )
    used_vcpus = models.PositiveIntegerField(default=0, verbose_name='Использовано vCPU')

    # ── RAM (MB) ───────────────────────────
    max_ram_mb = models.PositiveIntegerField(
        default=20480, validators=[MinValueValidator(512)],
        verbose_name='Макс. RAM (MB)'
    )
    used_ram_mb = models.PositiveIntegerField(default=0, verbose_name='Использовано RAM (MB)')

    # ── Диск (GB) ──────────────────────────
    max_disk_gb = models.PositiveIntegerField(
        default=500, validators=[MinValueValidator(10)],
        verbose_name='Макс. диск (GB)'
    )
    used_disk_gb = models.PositiveIntegerField(default=0, verbose_name='Использовано диска (GB)')

    # ── Лимит VM ──────────────────────────
    max_vms = models.PositiveIntegerField(
        default=10, validators=[MinValueValidator(1)],
        verbose_name='Макс. VM'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'resource_quotas'
        verbose_name = 'Квота ресурсов'
        verbose_name_plural = 'Квоты ресурсов'

    def __str__(self):
        return f"Quota: {self.organization.name}"

    # ── Проверки ──────────────────────────

    def check_vcpu(self, requested: int) -> bool:
        return (self.used_vcpus + requested) <= self.max_vcpus

    def check_ram(self, requested_mb: int) -> bool:
        return (self.used_ram_mb + requested_mb) <= self.max_ram_mb

    def check_disk(self, requested_gb: int) -> bool:
        return (self.used_disk_gb + requested_gb) <= self.max_disk_gb

    def check_vm_count(self) -> bool:
        """Проверяет, не превышен ли лимит VM. Счётчик берётся из живых VM."""
        active_count = self.organization.virtual_machines.exclude(
            status__in=['deleted', 'deleting']
        ).count()
        return active_count < self.max_vms

    # ── Операции ─────────────────────────

    def allocate(self, vcpus: int, ram_mb: int, disk_gb: int):
        """Зарезервировать ресурсы. Вызывать только внутри SELECT FOR UPDATE транзакции."""
        self.used_vcpus += vcpus
        self.used_ram_mb += ram_mb
        self.used_disk_gb += disk_gb
        self.save(update_fields=['used_vcpus', 'used_ram_mb', 'used_disk_gb', 'updated_at'])

    def release(self, vcpus: int, ram_mb: int, disk_gb: int):
        """Освободить ресурсы. Вызывать только внутри SELECT FOR UPDATE транзакции."""
        self.used_vcpus = max(0, self.used_vcpus - vcpus)
        self.used_ram_mb = max(0, self.used_ram_mb - ram_mb)
        self.used_disk_gb = max(0, self.used_disk_gb - disk_gb)
        self.save(update_fields=['used_vcpus', 'used_ram_mb', 'used_disk_gb', 'updated_at'])

    # ── Утилиты ───────────────────────────

    @property
    def vcpu_usage_pct(self) -> float:
        return round((self.used_vcpus / self.max_vcpus) * 100, 1) if self.max_vcpus else 0.0

    @property
    def ram_usage_pct(self) -> float:
        return round((self.used_ram_mb / self.max_ram_mb) * 100, 1) if self.max_ram_mb else 0.0

    @property
    def disk_usage_pct(self) -> float:
        return round((self.used_disk_gb / self.max_disk_gb) * 100, 1) if self.max_disk_gb else 0.0

    def as_dict(self) -> dict:
        return {
            'vcpu':  {'used': self.used_vcpus,  'max': self.max_vcpus,  'pct': self.vcpu_usage_pct},
            'ram':   {'used': self.used_ram_mb,  'max': self.max_ram_mb,  'pct': self.ram_usage_pct},
            'disk':  {'used': self.used_disk_gb, 'max': self.max_disk_gb, 'pct': self.disk_usage_pct},
            'vms':   {'max': self.max_vms},
        }
