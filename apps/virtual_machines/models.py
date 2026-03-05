import uuid
from django.db import models
from django.core.validators import MinValueValidator
from apps.accounts.models import Organization, User
from apps.hypervisors.models import Hypervisor


class VirtualMachine(models.Model):
    """Виртуальная машина — основная сущность IaaS."""

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        CREATING  = 'creating',  'Creating'
        RUNNING   = 'running',   'Running'
        STOPPED   = 'stopped',   'Stopped'
        PAUSED    = 'paused',    'Paused'
        RESTARTING = 'restarting', 'Restarting'
        ERROR     = 'error',     'Error'
        DELETING  = 'deleting',  'Deleting'
        DELETED   = 'deleted',   'Deleted'

    class OSType(models.TextChoices):
        UBUNTU_22  = 'ubuntu-22.04',   'Ubuntu 22.04 LTS'
        UBUNTU_20  = 'ubuntu-20.04',   'Ubuntu 20.04 LTS'
        DEBIAN_12  = 'debian-12',      'Debian 12'
        CENTOS_9   = 'centos-9',       'CentOS Stream 9'
        ROCKY_9    = 'rocky-9',        'Rocky Linux 9'
        WIN_2022   = 'windows-2022',   'Windows Server 2022'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='Имя VM')
    description = models.TextField(blank=True, verbose_name='Описание')

    # ── Мультитенантность ────────────────
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.SET_NULL,  
        null=True, blank=True,  
        related_name='virtual_machines', verbose_name='Организация'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_vms', verbose_name='Создал'
    )

    # ── Ресурсы ──────────────────────────
    vcpus    = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name='vCPU')
    ram_mb   = models.PositiveIntegerField(validators=[MinValueValidator(512)], verbose_name='RAM (MB)')
    disk_gb  = models.PositiveIntegerField(validators=[MinValueValidator(10)], verbose_name='Диск (GB)')
    os_type  = models.CharField(max_length=50, choices=OSType.choices, verbose_name='ОС')

    # ── Инфраструктура ───────────────────
    hypervisor = models.ForeignKey(
        Hypervisor, on_delete=models.SET_NULL, null=True,
        related_name='virtual_machines', verbose_name='Гипервизор'
    )
    libvirt_uuid = models.UUIDField(null=True, blank=True, verbose_name='UUID в libvirt')
    ip_address   = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP-адрес')

    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'virtual_machines'
        unique_together = ('organization', 'name')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['hypervisor', 'status']),
        ]
        verbose_name = 'Виртуальная машина'
        verbose_name_plural = 'Виртуальные машины'

    def __str__(self):
        return f"{self.name} [{self.status}] @ {self.organization.name}"

    @property
    def is_actionable(self) -> bool:
        """Можно ли выполнять операции над VM."""
        return self.status not in [
            self.Status.CREATING, self.Status.DELETING, self.Status.DELETED
        ]
