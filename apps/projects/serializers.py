from rest_framework import serializers
from .models import Project, Transaction, UsersDailyStats, DowntimeEvent, ResourcePoint

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'name', 'amount', 'date']

class UsersDailyStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsersDailyStats
        fields = ['date', 'total_users', 'active_users', 'inactive_users']

class DowntimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DowntimeEvent
        fields = ['down_at', 'restored_at', 'duration_minutes']

class ResourcePointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourcePoint
        fields = ['timestamp', 'load']

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'plan_type', 'time_on_platform_days', 'created_at']
