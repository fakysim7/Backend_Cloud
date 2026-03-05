# apps/projects/views.py
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Avg, Sum
from apps.projects.models import Project
from apps.projects.serializers import (
    ProjectSerializer, TransactionSerializer,
    DowntimeSerializer, UsersDailyStatsSerializer, ResourcePointSerializer
)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        org = self.request.current_organization  # Мультитенант
        return Project.objects.filter(organization=org)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Полная статистика проекта"""
        project = self.get_object()

        # Подписка организации для получения цен плана
        subscription = getattr(project.organization, 'subscription', None)
        plan = subscription.plan if subscription else None

        return Response({
            'projectInfo': {
                'name': project.name,
                'description': project.description,
                'timeOnPlatform': f"{project.time_on_platform_days} days",
                'plan': {
                    'type': project.plan_type,
                    'annual': float(plan.annual_price) if plan else None,
                    'monthly': float(plan.monthly_price) if plan else None,
                }
            },
            'projectFinance': {
                'totalSpent': project.transactions.aggregate(
                    total=Sum('amount')
                )['total'] or 0,
                'transactions': TransactionSerializer(
                    project.transactions.all()[:10], many=True
                ).data
            },
            'users': UsersDailyStatsSerializer(
                project.users_stats.all()[:30], many=True
            ).data,
            'downTime': DowntimeSerializer(
                project.downtime_events.all()[:10], many=True
            ).data,
            'resourceUsage': {
                'cpu': ResourcePointSerializer(
                    project.resource_points.filter(
                        metric_type='cpu'
                    ).order_by('-timestamp')[:100],
                    many=True
                ).data,
                'memory': ResourcePointSerializer(
                    project.resource_points.filter(
                        metric_type='memory'
                    ).order_by('-timestamp')[:100],
                    many=True
                ).data,
                'ram': ResourcePointSerializer(
                    project.resource_points.filter(
                        metric_type='ram'
                    ).order_by('-timestamp')[:100],
                    many=True
                ).data,
            }
        })