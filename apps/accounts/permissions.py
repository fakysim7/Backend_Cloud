from rest_framework.permissions import BasePermission
from django.shortcuts import get_object_or_404
from apps.accounts.models import OrganizationMembership, Organization

class IsOrganizationMember(BasePermission):
    def has_permission(self, request, view):
        org = getattr(request, 'current_organization', None)
        if not org:
            return False
        
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=org,
            role__in=['owner', 'admin', 'member']
        ).exists()
    
    def has_object_permission(self, request, view, obj):
        org = getattr(request, 'current_organization', None)
        if not org:
            return False
        return obj.organization == org
