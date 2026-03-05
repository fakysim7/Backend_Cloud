import logging
from django.http import JsonResponse
from apps.accounts.models import OrganizationMembership

logger = logging.getLogger(__name__)

# URL-пути, которые не требуют организационного контекста
TENANT_EXEMPT_PATHS = [
    '/admin/',
    '/api/auth/',
    '/api/schema/',
    '/api/docs/',
    '/api/redoc/',
    '/api/organizations/',  # создание организации
    '/api/auth/register/',
]


class TenantMiddleware:
    """
    Определяет организацию пользователя из заголовка X-Organization-Slug.
    Устанавливает request.current_organization и request.current_role.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_organization = None
        request.current_role = None

        # Пропускаем пути, которые не требуют тенанта
        if any(request.path.startswith(p) for p in TENANT_EXEMPT_PATHS):
            return self.get_response(request)

        if request.user.is_authenticated:
            slug = request.headers.get('X-Organization-Slug')

            if slug:
                try:
                    membership = OrganizationMembership.objects.select_related(
                        'organization'
                    ).get(
                        user=request.user,
                        organization__slug=slug,
                        organization__is_active=True,
                    )
                    request.current_organization = membership.organization
                    request.current_role = membership.role
                except OrganizationMembership.DoesNotExist:
                    return JsonResponse(
                        {
                            'error': 'Организация не найдена или у вас нет доступа к ней.',
                            'code': 'invalid_organization',
                        },
                        status=403,
                    )

        return self.get_response(request)
