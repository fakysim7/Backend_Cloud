"""
Интеграционные тесты API виртуальных машин.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, Organization, OrganizationMembership
from apps.quotas.models import ResourceQuota
from apps.hypervisors.models import Hypervisor
from apps.virtual_machines.models import VirtualMachine


class VMAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Создаём пользователя и организацию
        self.user = User.objects.create_user(
            email='test@example.com', username='testuser', password='pass123'
        )
        self.org = Organization.objects.create(name='Test Org', slug='test-org')
        OrganizationMembership.objects.create(
            user=self.user, organization=self.org,
            role=OrganizationMembership.Role.OWNER,
        )
        self.quota = ResourceQuota.objects.create(
            organization=self.org,
            max_vcpus=16, max_ram_mb=32768, max_disk_gb=500, max_vms=10,
        )
        self.hypervisor = Hypervisor.objects.create(
            name='test-hv', host='127.0.0.1',
            total_vcpus=32, total_ram_mb=65536, total_disk_gb=2000,
            status=Hypervisor.Status.ONLINE,
        )

        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_ORGANIZATION_SLUG='test-org')

    @patch('apps.virtual_machines.views.create_vm_task')
    def test_create_vm_success(self, mock_task):
        mock_task.delay = MagicMock()
        response = self.client.post('/api/vms/', {
            'name': 'my-test-vm',
            'vcpus': 2,
            'ram_mb': 2048,
            'disk_gb': 50,
            'os_type': 'ubuntu-22.04',
        })
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(VirtualMachine.objects.filter(name='my-test-vm').exists())
        mock_task.delay.assert_called_once()

    @patch('apps.virtual_machines.views.create_vm_task')
    def test_create_vm_quota_exceeded(self, mock_task):
        """Создание VM сверх квоты должно вернуть 422."""
        response = self.client.post('/api/vms/', {
            'name': 'big-vm',
            'vcpus': 99,  # превышает max_vcpus=16
            'ram_mb': 1024,
            'disk_gb': 50,
            'os_type': 'ubuntu-22.04',
        })
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        mock_task.delay.assert_not_called()

    def test_list_vms_scoped_to_org(self):
        """Пользователь видит только VM своей организации."""
        other_org = Organization.objects.create(name='Other Org', slug='other-org')
        ResourceQuota.objects.create(organization=other_org)

        VirtualMachine.objects.create(
            name='my-vm', organization=self.org,
            created_by=self.user, hypervisor=self.hypervisor,
            vcpus=1, ram_mb=512, disk_gb=10, os_type='ubuntu-22.04',
        )
        VirtualMachine.objects.create(
            name='other-vm', organization=other_org,
            vcpus=1, ram_mb=512, disk_gb=10, os_type='ubuntu-22.04',
        )

        response = self.client.get('/api/vms/')
        self.assertEqual(response.status_code, 200)
        names = [vm['name'] for vm in response.data['results']]
        self.assertIn('my-vm', names)
        self.assertNotIn('other-vm', names)

    def test_create_vm_without_org_header(self):
        """Без заголовка X-Organization-Slug — 400."""
        self.client.credentials()  # убираем заголовок
        response = self.client.post('/api/vms/', {
            'name': 'vm', 'vcpus': 1, 'ram_mb': 512, 'disk_gb': 10, 'os_type': 'ubuntu-22.04',
        })
        self.assertIn(response.status_code, [400, 403])
