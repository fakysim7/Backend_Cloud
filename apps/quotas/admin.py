from django.contrib import admin
from .models import ResourceQuota


@admin.register(ResourceQuota)
class ResourceQuotaAdmin(admin.ModelAdmin):
    list_display = [
        'organization', 'max_vcpus', 'used_vcpus',
        'max_ram_mb', 'used_ram_mb', 'max_disk_gb', 'used_disk_gb', 'max_vms'
    ]
    readonly_fields = ['used_vcpus', 'used_ram_mb', 'used_disk_gb', 'updated_at']
    search_fields = ['organization__name']
