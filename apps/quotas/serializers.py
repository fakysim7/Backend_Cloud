from rest_framework import serializers
from .models import ResourceQuota


class ResourceQuotaSerializer(serializers.ModelSerializer):
    vcpu_usage_pct = serializers.FloatField(read_only=True)
    ram_usage_pct = serializers.FloatField(read_only=True)
    disk_usage_pct = serializers.FloatField(read_only=True)

    # Удобные поля в GB и GHz для фронта
    max_ram_gb = serializers.SerializerMethodField()
    used_ram_gb = serializers.SerializerMethodField()

    class Meta:
        model = ResourceQuota
        fields = [
            # vCPU
            'max_vcpus', 'used_vcpus', 'vcpu_usage_pct',
            # RAM
            'max_ram_mb', 'used_ram_mb', 'max_ram_gb', 'used_ram_gb', 'ram_usage_pct',
            # Disk
            'max_disk_gb', 'used_disk_gb', 'disk_usage_pct',
            # VMs
            'max_vms',
            'updated_at',
        ]
        read_only_fields = [
            'used_vcpus', 'used_ram_mb', 'used_disk_gb',
            'vcpu_usage_pct', 'ram_usage_pct', 'disk_usage_pct',
            'max_ram_gb', 'used_ram_gb', 'updated_at',
        ]

    def get_max_ram_gb(self, obj):
        return round(obj.max_ram_mb / 1024, 2)

    def get_used_ram_gb(self, obj):
        return round(obj.used_ram_mb / 1024, 2)
