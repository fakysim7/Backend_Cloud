from rest_framework import serializers
from .models import Project, Transaction, UsersDailyStats, DowntimeEvent, ResourcePoint

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'name', 'amount', 'date']

class UsersDailyStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsersDailyStats
        fields = ['date', 'users', 'active', 'inactive', 'total']

class DowntimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DowntimeEvent
        fields = ['down', 'restored']

class ResourcePointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourcePoint
        fields = ['time', 'load']

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'plan_type', 'time_on_platform_days', 'created_at']
