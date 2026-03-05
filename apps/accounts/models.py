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
