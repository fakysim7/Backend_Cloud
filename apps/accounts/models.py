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


class Client(models.Model):
    """Публичная информация клиента организации."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name='client'
    )
    position = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name()


class Plan(models.Model):
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)

    max_projects = models.PositiveIntegerField()
    max_users = models.PositiveIntegerField()
    max_storage_gb = models.PositiveIntegerField()

    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    annual_price = models.DecimalField(max_digits=10, decimal_places=2)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name


class OrganizationSubscription(models.Model):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name='subscription'
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)

    current_projects = models.PositiveIntegerField(default=0)
    current_users = models.PositiveIntegerField(default=0)
    current_storage_gb = models.PositiveIntegerField(default=0)

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

    def __str__(self):
        return f"{self.organization.name} — {self.plan.display_name}"