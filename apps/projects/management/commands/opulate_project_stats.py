from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import Project, UsersDailyStats, ResourcePoint
import random

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for project in Project.objects.all():
            # Пользователи (ежедневно)
            UsersDailyStats.objects.create(
                project=project,
                date=timezone.now().date(),
                total_users=random.randint(10, 100),
                active_users=random.randint(5, 90),
                inactive_users=... 
            )
            
            # Ресурсы (каждые 5 мин)
            for metric in ['cpu', 'memory', 'ram']:
                ResourcePoint.objects.create(
                    project=project,
                    timestamp=timezone.now(),
                    metric_type=metric,
                    load=random.uniform(10.0, 90.0)
                )