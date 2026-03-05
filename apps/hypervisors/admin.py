from django.contrib import admin
from .models import Hypervisor


@admin.register(Hypervisor)
class HypervisorAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'host', 'status',
        'total_vcpus', 'used_vcpus',
        'total_ram_mb', 'used_ram_mb',
        'total_disk_gb', 'used_disk_gb',
        'last_heartbeat',
    ]
    list_filter = ['status']
    readonly_fields = ['used_vcpus', 'used_ram_mb', 'used_disk_gb', 'last_heartbeat', 'created_at']
