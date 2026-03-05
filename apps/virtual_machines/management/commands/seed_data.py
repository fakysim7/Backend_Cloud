"""
python manage.py seed_data
Создаёт тестовые данные для разработки.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User, Organization, OrganizationMembership
from apps.quotas.models import ResourceQuota
from apps.hypervisors.models import Hypervisor


class Command(BaseCommand):
    help = 'Создать тестовые данные: пользователи, организации, квоты, гипервизоры'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Создание тестовых данных...')

        # Superuser
        admin, _ = User.objects.get_or_create(
            email='admin@iaas.local',
            defaults={'username': 'admin', 'is_staff': True, 'is_superuser': True},
        )
        admin.set_password('admin123')
        admin.save()
        self.stdout.write(f'  ✓ Admin: admin@iaas.local / admin123')

        # Тестовые организации
        for i in range(1, 4):
            org, created = Organization.objects.get_or_create(
                slug=f'org-{i}',
                defaults={'name': f'Organization {i}'},
            )

            # Квота
            ResourceQuota.objects.get_or_create(
                organization=org,
                defaults={
                    'max_vcpus':   20,
                    'max_ram_mb':  40960,  # 40 GB
                    'max_disk_gb': 1000,
                    'max_vms':     20,
                },
            )

            # Пользователь-владелец
            user, _ = User.objects.get_or_create(
                email=f'owner{i}@iaas.local',
                defaults={'username': f'owner{i}'},
            )
            user.set_password('pass123')
            user.save()

            OrganizationMembership.objects.get_or_create(
                user=user, organization=org,
                defaults={'role': OrganizationMembership.Role.OWNER},
            )

            if created:
                self.stdout.write(f'  ✓ Org: {org.name} (owner: {user.email} / pass123)')

        # Гипервизоры
        hypervisors = [
            {'name': 'hv-01', 'host': '192.168.1.10', 'total_vcpus': 64, 'total_ram_mb': 131072, 'total_disk_gb': 10000},
            {'name': 'hv-02', 'host': '192.168.1.11', 'total_vcpus': 64, 'total_ram_mb': 131072, 'total_disk_gb': 10000},
        ]
        for hv_data in hypervisors:
            hv, created = Hypervisor.objects.get_or_create(
                name=hv_data['name'],
                defaults={**hv_data, 'status': Hypervisor.Status.ONLINE},
            )
            if created:
                self.stdout.write(f'  ✓ Hypervisor: {hv.name} ({hv.host})')

        self.stdout.write(self.style.SUCCESS('\nГотово! Тестовые данные созданы.'))
