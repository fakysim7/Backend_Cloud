from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from .models import Organization, OrganizationMembership, User
from .serializers import (
    RegisterSerializer, UserSerializer,
    OrganizationSerializer, OrganizationMembershipSerializer,
    InviteUserSerializer,
)
from apps.quotas.models import ResourceQuota
from core.permissions import IsOrganizationAdmin, IsOrganizationOwner


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя."""
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    """Текущий пользователь."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class OrganizationViewSet(viewsets.ModelViewSet):
    """CRUD организаций + управление участниками."""
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user,
            is_active=True,
        ).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        org = serializer.save()
        # Создатель автоматически становится Owner
        OrganizationMembership.objects.create(
            user=self.request.user,
            organization=org,
            role=OrganizationMembership.Role.OWNER,
        )
        # Создаём квоты по умолчанию
        ResourceQuota.objects.create(organization=org)

    # ── Участники ──────────────────────────────────────────────────

    @action(detail=True, methods=['get'], url_path='members')
    def members(self, request, pk=None):
        org = self.get_object()
        qs = OrganizationMembership.objects.filter(organization=org).select_related('user')
        serializer = OrganizationMembershipSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='members/invite',
            permission_classes=[IsOrganizationAdmin])
    def invite(self, request, pk=None):
        """Пригласить пользователя по email."""
        org = self.get_object()
        serializer = InviteUserSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.instance or User.objects.get(email=serializer.validated_data['email'])
        role = serializer.validated_data['role']

        membership, created = OrganizationMembership.objects.get_or_create(
            user=user, organization=org,
            defaults={'role': role}
        )
        if not created:
            return Response({'error': 'Пользователь уже является участником.'}, status=400)

        return Response(OrganizationMembershipSerializer(membership).data, status=201)

    @action(detail=True, methods=['patch', 'delete'],
            url_path='members/(?P<member_id>[^/.]+)',
            permission_classes=[IsOrganizationAdmin])
    def member_detail(self, request, pk=None, member_id=None):
        """Изменить роль или удалить участника."""
        org = self.get_object()
        try:
            membership = OrganizationMembership.objects.get(id=member_id, organization=org)
        except OrganizationMembership.DoesNotExist:
            return Response({'error': 'Участник не найден.'}, status=404)

        if request.method == 'DELETE':
            if membership.role == OrganizationMembership.Role.OWNER:
                return Response({'error': 'Нельзя удалить владельца организации.'}, status=400)
            membership.delete()
            return Response(status=204)

        serializer = OrganizationMembershipSerializer(
            membership, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
