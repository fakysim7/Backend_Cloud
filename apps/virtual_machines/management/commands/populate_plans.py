# В apps/accounts/management/commands/populate_plans.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import Plan

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        Plan.objects.bulk_create([
            Plan(name='basic', display_name='Basic', max_projects=10, max_users=5, max_storage_gb=25, monthly_price=29.99, annual_price=299.99),
            Plan(name='professional', display_name='Professional', max_projects=50, max_users=25, max_storage_gb=100, monthly_price=99.99, annual_price=999.99),
            Plan(name='enterprise', display_name='Enterprise', max_projects=999999, max_users=100, max_storage_gb=1024, monthly_price=299.99, annual_price=2999.99),
        ])
        self.stdout.write(self.style.SUCCESS('Plans created!'))
