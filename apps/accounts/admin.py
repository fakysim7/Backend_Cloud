from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Organization, OrganizationMembership


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_active', 'date_joined']
    search_fields = ['email', 'username']
    ordering = ['email']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': []}),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'joined_at']
    list_filter = ['role', 'organization']
    search_fields = ['user__email', 'organization__name']
