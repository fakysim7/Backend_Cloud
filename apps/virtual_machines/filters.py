import django_filters
from .models import VirtualMachine


class VirtualMachineFilter(django_filters.FilterSet):
    status   = django_filters.ChoiceFilter(choices=VirtualMachine.Status.choices)
    os_type  = django_filters.ChoiceFilter(choices=VirtualMachine.OSType.choices)
    vcpus    = django_filters.NumberFilter()
    vcpus_min = django_filters.NumberFilter(field_name='vcpus', lookup_expr='gte')
    vcpus_max = django_filters.NumberFilter(field_name='vcpus', lookup_expr='lte')
    ram_min  = django_filters.NumberFilter(field_name='ram_mb', lookup_expr='gte')
    ram_max  = django_filters.NumberFilter(field_name='ram_mb', lookup_expr='lte')
    created_after  = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = VirtualMachine
        fields = [
            'status', 'os_type', 'vcpus',
            'vcpus_min', 'vcpus_max',
            'ram_min', 'ram_max',
            'created_after', 'created_before',
        ]
