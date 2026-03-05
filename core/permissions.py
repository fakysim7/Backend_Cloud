from rest_framework.permissions import BasePermission
from apps.accounts.models import OrganizationMembership


class HasOrganizationContext(BasePermission):
    """Требует наличия организационного контекста в запросе."""
    message = 'Укажите заголовок X-Organization-Slug.'

    def has_permission(self, request, view):
        return request.current_organization is not None


class IsOrganizationMember(BasePermission):
    """Пользователь — участник организации (любая роль)."""
    message = 'Вы не являетесь участником этой организации.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.current_organization is not None
        )

    def has_object_permission(self, request, view, obj):
        org = getattr(obj, 'organization', obj)
        return OrganizationMembership.objects.filter(
            user=request.user, organization=org
        ).exists()


class IsOrganizationAdmin(BasePermission):
    """Пользователь — владелец или администратор организации."""
    message = 'Требуются права администратора организации.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.current_organization is None:
            return False
        return request.current_role in [
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.ADMIN,
        ]


class IsOrganizationOwner(BasePermission):
    """Пользователь — владелец организации."""
    message = 'Требуются права владельца организации.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.current_organization is None:
            return False
        return request.current_role == OrganizationMembership.Role.OWNER


class IsReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in ('GET', 'HEAD', 'OPTIONS')
