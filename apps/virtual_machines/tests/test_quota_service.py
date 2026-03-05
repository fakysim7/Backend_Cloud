"""
Тесты QuotaService — атомарный контроль ресурсов.
"""
from django.test import TestCase
from apps.accounts.models import User, Organization, OrganizationMembership
from apps.quotas.models import ResourceQuota
from apps.virtual_machines.services.quota_service import QuotaService
from core.exceptions import QuotaExceededError


class QuotaServiceTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Test Org', slug='test-org')
        self.quota = ResourceQuota.objects.create(
            organization=self.org,
            max_vcpus=4,
            max_ram_mb=4096,
            max_disk_gb=100,
            max_vms=3,
        )

    def test_allocate_within_limits(self):
        QuotaService.check_and_allocate(self.org, vcpus=2, ram_mb=1024, disk_gb=20)
        self.quota.refresh_from_db()
        self.assertEqual(self.quota.used_vcpus, 2)
        self.assertEqual(self.quota.used_ram_mb, 1024)
        self.assertEqual(self.quota.used_disk_gb, 20)

    def test_vcpu_exceeded_raises_error(self):
        with self.assertRaises(QuotaExceededError) as ctx:
            QuotaService.check_and_allocate(self.org, vcpus=5, ram_mb=512, disk_gb=10)
        self.assertTrue(any('vCPU' in e for e in ctx.exception.errors))

    def test_ram_exceeded_raises_error(self):
        with self.assertRaises(QuotaExceededError) as ctx:
            QuotaService.check_and_allocate(self.org, vcpus=1, ram_mb=5000, disk_gb=10)
        self.assertTrue(any('RAM' in e for e in ctx.exception.errors))

    def test_release_restores_quota(self):
        QuotaService.check_and_allocate(self.org, vcpus=2, ram_mb=1024, disk_gb=20)
        QuotaService.release(self.org, vcpus=2, ram_mb=1024, disk_gb=20)
        self.quota.refresh_from_db()
        self.assertEqual(self.quota.used_vcpus, 0)
        self.assertEqual(self.quota.used_ram_mb, 0)

    def test_multiple_errors_reported(self):
        """Если превышено несколько лимитов — все ошибки возвращаются."""
        with self.assertRaises(QuotaExceededError) as ctx:
            QuotaService.check_and_allocate(self.org, vcpus=99, ram_mb=99999, disk_gb=9999)
        self.assertGreater(len(ctx.exception.errors), 1)

    def test_usage_percent_properties(self):
        self.quota.used_vcpus = 2
        self.quota.save()
        self.assertEqual(self.quota.vcpu_usage_pct, 50.0)
