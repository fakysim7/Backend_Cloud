import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """Превышена квота ресурсов организации."""

    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Quota exceeded: {'; '.join(errors)}")


class HypervisorUnavailableError(Exception):
    """Нет доступных гипервизоров с достаточными ресурсами."""
    pass


class VMOperationError(Exception):
    """Ошибка операции над виртуальной машиной."""
    pass


def custom_exception_handler(exc, context):
    """Единый обработчик исключений для API."""
    response = exception_handler(exc, context)

    if isinstance(exc, QuotaExceededError):
        return Response(
            {
                'error': 'Превышена квота ресурсов.',
                'code': 'quota_exceeded',
                'details': exc.errors,
            },
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if isinstance(exc, HypervisorUnavailableError):
        return Response(
            {'error': str(exc), 'code': 'hypervisor_unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if isinstance(exc, VMOperationError):
        return Response(
            {'error': str(exc), 'code': 'vm_operation_error'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if response is not None:
        response.data = {
            'error': response.data,
            'code': 'error',
            'status_code': response.status_code,
        }

    return response
