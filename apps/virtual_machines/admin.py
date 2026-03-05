from django.contrib import admin
from .models import VirtualMachine


@admin.register(VirtualMachine)
class VirtualMachineAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'organization', 'status', 'vcpus',
        'ram_mb', 'disk_gb', 'os_type', 'hypervisor',
        'ip_address', 'created_at',
    ]
    list_filter = ['status', 'os_type', 'organization', 'hypervisor']
    search_fields = ['name', 'ip_address', 'libvirt_uuid']
    readonly_fields = [
        'id', 'libvirt_uuid', 'created_at', 'updated_at', 'deleted_at',
        'created_by', 'error_message',
    ]
    raw_id_fields = ['organization', 'created_by', 'hypervisor']
