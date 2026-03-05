"""
Выбор гипервизора для размещения новой VM.
Поддерживает разные стратегии планирования.
"""
from typing import Optional
from apps.hypervisors.models import Hypervisor


def select_best_hypervisor(
    vcpus: int,
    ram_mb: int,
    disk_gb: int,
    strategy: str = 'spread',
) -> Optional[Hypervisor]:
    """
    Выбирает подходящий гипервизор.

    Стратегии:
      spread  — равномерно распределяет нагрузку (по умолчанию).
                Выбирает узел с наибольшим количеством свободных CPU.
      pack    — упаковывает VM плотнее (экономит электроэнергию).
                Выбирает узел с наименьшим количеством свободных CPU.
    """
    candidates = Hypervisor.objects.filter(
        status=Hypervisor.Status.ONLINE
    ).extra(
        select={
            'free_cpu': 'total_vcpus - used_vcpus',
            'free_ram': 'total_ram_mb - used_ram_mb',
        }
    )

    if strategy == 'pack':
        candidates = candidates.order_by('free_cpu', 'free_ram')
    else:  # spread
        candidates = candidates.order_by('-free_cpu', '-free_ram')

    for hypervisor in candidates:
        if hypervisor.has_capacity(vcpus, ram_mb, disk_gb):
            return hypervisor

    return None
