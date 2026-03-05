from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from apps.accounts.models import Organization

class Project(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Тарифный план проекта (ссылка на общий план организации)
    plan_type = models.CharField(max_length=20)  # 'basic', 'professional', 'enterprise'
    
    # Статистика времени (обновляется cron)
    time_on_platform_days = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['organization', 'name']
        indexes = [models.Index(fields=['organization', 'name'])]
    
    def __str__(self):
        return f"{self.organization.slug}/{self.name}"

class Transaction(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='transactions')
    name = models.CharField(max_length=255)  # "Monthly sub", "CPU overusage"
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField()
    
    class Meta:
        indexes = [models.Index(fields=['project', 'date'])]
        ordering = ['-date']

class UsersDailyStats(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='users_stats')
    date = models.DateField()
    total_users = models.PositiveIntegerField()
    active_users = models.PositiveIntegerField()
    inactive_users = models.PositiveIntegerField()
    
    class Meta:
        unique_together = ['project', 'date']
        indexes = [models.Index(fields=['project', 'date'])]
        ordering = ['-date']

class DowntimeEvent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='downtime_events')
    down_at = models.DateTimeField()
    restored_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        indexes = [models.Index(fields=['project', 'down_at'])]
        ordering = ['-down_at']

class ResourcePoint(models.Model):
    METRIC_CHOICES = [
        ('cpu', 'CPU'),
        ('memory', 'Memory'), 
        ('ram', 'RAM')
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='resource_points')
    timestamp = models.DateTimeField()
    metric_type = models.CharField(max_length=10, choices=METRIC_CHOICES)
    load = models.FloatField()  # 0.0-100.0%
    
    class Meta:
        indexes = [
            models.Index(fields=['project', 'metric_type', 'timestamp']),
            models.Index(fields=['timestamp'])
        ]
        ordering = ['timestamp']
