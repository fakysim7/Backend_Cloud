import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Кастомная модель пользователя с UUID и email-авторизацией."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email


class Organization(models.Model):
    """Тенант — организация. Изолирует ресурсы между клиентами."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, verbose_name='Название')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='Slug')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations'
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'
        ordering = ['name']

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    """Связь пользователя с организацией + роль."""

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'
        VIEWER = 'viewer', 'Viewer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='memberships', verbose_name='Пользователь'
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        related_name='memberships', verbose_name='Организация'
    )
    role = models.CharField(
        max_length=20, choices=Role.choices,
        default=Role.MEMBER, verbose_name='Роль'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organization_memberships'
        unique_together = ('user', 'organization')
        verbose_name = 'Участник организации'
        verbose_name_plural = 'Участники организации'

    def __str__(self):
        return f"{self.user.email} @ {self.organization.name} [{self.role}]"

    @property
    def can_manage_vms(self) -> bool:
        return self.role in [self.Role.OWNER, self.Role.ADMIN, self.Role.MEMBER]

    @property
    def can_manage_members(self) -> bool:
        return self.role in [self.Role.OWNER, self.Role.ADMIN]


# apps/accounts/models.py
class Client(models.Model):
    # Публичная информация клиента
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    
    # Связь с организацией (мультитенантность)
    organization = models.OneToOneField('Organization', on_delete=CASCADE, related_name='client')
    
    # Должность
    position = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Plan(models.Model):
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('professional', 'Professional'), 
        ('enterprise', 'Enterprise')
    ]
    
    name = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    
    # Ограничения
    max_projects = models.PositiveIntegerField()
    max_users = models.PositiveIntegerField()
    max_storage_gb = models.PositiveIntegerField()
    
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    annual_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    is_active = models.BooleanField(default=True)

class OrganizationSubscription(models.Model):
    organization = models.OneToOneField('Organization', on_delete=CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=PROTECT)
    
    # Текущие показатели (сравниваются с лимитами)
    current_projects = models.PositiveIntegerField(default=0)
    current_users = models.PositiveIntegerField(default=0)
    current_storage_gb = models.PositiveIntegerField(default=0)
    
    # Статус подписки
    is_active = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    @property
    def is_over_limit(self):
        return (
            self.current_projects > self.plan.max_projects or
            self.current_users > self.plan.max_users or
            self.current_storage_gb > self.plan.max_storage_gb
        )


class Project(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Тарифный план проекта (ссылка на общий план организации)
    plan_type = models.CharField(max_length=20)  # 'basic', 'professional', 'enterprise'
    
    # Статистика времени (обновляется cron)
    time_on_platform_days = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['organization', 'name']
        indexes = [models.Index(fields=['organization', 'name'])]
    
    def __str__(self):
        return f"{self.organization.slug}/{self.name}"

class Transaction(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='transactions')
    name = models.CharField(max_length=255)  # "Monthly sub", "CPU overusage"
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField()
    
    class Meta:
        indexes = [models.Index(fields=['project', 'date'])]
        ordering = ['-date']

class UsersDailyStats(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='users_stats')
    date = models.DateField()
    total_users = models.PositiveIntegerField()
    active_users = models.PositiveIntegerField()
    inactive_users = models.PositiveIntegerField()
    
    class Meta:
        unique_together = ['project', 'date']
        indexes = [models.Index(fields=['project', 'date'])]
        ordering = ['-date']

class DowntimeEvent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='downtime_events')
    down_at = models.DateTimeField()
    restored_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        indexes = [models.Index(fields=['project', 'down_at'])]
        ordering = ['-down_at']

class ResourcePoint(models.Model):
    METRIC_CHOICES = [
        ('cpu', 'CPU'),
        ('memory', 'Memory'), 
        ('ram', 'RAM')
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='resource_points')
    timestamp = models.DateTimeField()
    metric_type = models.CharField(max_length=10, choices=METRIC_CHOICES)
    load = models.FloatField()  # 0.0-100.0%
    
    class Meta:
        indexes = [
            models.Index(fields=['project', 'metric_type', 'timestamp']),
            models.Index(fields=['timestamp'])
        ]
        ordering = ['timestamp']