from rest_framework import serializers
from .models import Hypervisor


class HypervisorSerializer(serializers.ModelSerializer):
    free_vcpus = serializers.IntegerField(read_only=True)
    free_ram_mb = serializers.IntegerField(read_only=True)
    free_disk_gb = serializers.IntegerField(read_only=True)
    vcpu_load_pct = serializers.SerializerMethodField()
    ram_load_pct = serializers.SerializerMethodField()
    vm_count = serializers.SerializerMethodField()

    class Meta:
        model = Hypervisor
        fields = [
            'id', 'name', 'host', 'port', 'status',
            'total_vcpus', 'used_vcpus', 'free_vcpus', 'vcpu_load_pct',
            'total_ram_mb', 'used_ram_mb', 'free_ram_mb', 'ram_load_pct',
            'total_disk_gb', 'used_disk_gb', 'free_disk_gb',
            'vm_count', 'last_heartbeat', 'created_at',
        ]
        read_only_fields = [
            'used_vcpus', 'used_ram_mb', 'used_disk_gb',
            'free_vcpus', 'free_ram_mb', 'free_disk_gb',
            'vcpu_load_pct', 'ram_load_pct', 'vm_count', 'last_heartbeat',
        ]

    def get_vcpu_load_pct(self, obj):
        return round((obj.used_vcpus / obj.total_vcpus) * 100, 1) if obj.total_vcpus else 0

    def get_ram_load_pct(self, obj):
        return round((obj.used_ram_mb / obj.total_ram_mb) * 100, 1) if obj.total_ram_mb else 0

    def get_vm_count(self, obj):
        return obj.virtual_machines.exclude(status__in=['deleted', 'deleting']).count()
