import uuid
from django.db import models
from django.core.validators import MinValueValidator


class Hypervisor(models.Model):
    """Физический узел гипервизора (KVM/libvirt)."""

    class Status(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        MAINTENANCE = 'maintenance', 'Maintenance'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name='Имя')
    host = models.GenericIPAddressField(verbose_name='IP-адрес')
    port = models.PositiveIntegerField(default=16509, verbose_name='Порт libvirt')

    # Физические ресурсы
    total_vcpus = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_ram_mb = models.PositiveIntegerField(validators=[MinValueValidator(512)])
    total_disk_gb = models.PositiveIntegerField(validators=[MinValueValidator(10)])

    # Текущее использование (обновляется Celery Beat)
    used_vcpus = models.PositiveIntegerField(default=0)
    used_ram_mb = models.PositiveIntegerField(default=0)
    used_disk_gb = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ONLINE
    )
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hypervisors'
        verbose_name = 'Гипервизор'
        verbose_name_plural = 'Гипервизоры'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.host}) [{self.status}]"

    def has_capacity(self, vcpus: int, ram_mb: int, disk_gb: int) -> bool:
        return (
            self.status == self.Status.ONLINE
            and (self.used_vcpus + vcpus) <= self.total_vcpus
            and (self.used_ram_mb + ram_mb) <= self.total_ram_mb
            and (self.used_disk_gb + disk_gb) <= self.total_disk_gb
        )

    @property
    def free_vcpus(self): return self.total_vcpus - self.used_vcpus

    @property
    def free_ram_mb(self): return self.total_ram_mb - self.used_ram_mb

    @property
    def free_disk_gb(self): return self.total_disk_gb - self.used_disk_gb
