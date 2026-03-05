from rest_framework import serializers
from .models import VirtualMachine


class VirtualMachineCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания VM — только входные данные."""

    class Meta:
        model = VirtualMachine
        fields = ['name', 'description', 'vcpus', 'ram_mb', 'disk_gb', 'os_type']

    def validate_vcpus(self, value):
        if not (1 <= value <= 64):
            raise serializers.ValidationError("vCPU должно быть от 1 до 64.")
        return value

    def validate_ram_mb(self, value):
        if not (512 <= value <= 524288):
            raise serializers.ValidationError("RAM: от 512MB до 524288MB (512 GB).")
        # Проверяем кратность 512MB
        if value % 512 != 0:
            raise serializers.ValidationError("RAM должна быть кратна 512MB.")
        return value

    def validate_disk_gb(self, value):
        if not (10 <= value <= 10000):
            raise serializers.ValidationError("Диск: от 10GB до 10000GB.")
        return value

    def validate_name(self, value):
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]{1,98}[a-zA-Z0-9]$', value):
            raise serializers.ValidationError(
                "Имя VM: только латинские буквы, цифры и дефис, от 3 до 100 символов."
            )
        return value.lower()


class VirtualMachineSerializer(serializers.ModelSerializer):
    """Полный сериализатор VM для чтения."""
    created_by_email  = serializers.EmailField(source='created_by.email', read_only=True)
    hypervisor_name   = serializers.CharField(source='hypervisor.name', read_only=True, default=None)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    ram_gb            = serializers.SerializerMethodField()

    class Meta:
        model = VirtualMachine
        fields = [
            'id', 'name', 'description',
            'vcpus', 'ram_mb', 'ram_gb', 'disk_gb', 'os_type',
            'status', 'error_message', 'ip_address',
            'organization_name', 'created_by_email',
            'hypervisor_name', 'libvirt_uuid',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_ram_gb(self, obj):
        return round(obj.ram_mb / 1024, 2)


class VirtualMachineListSerializer(serializers.ModelSerializer):
    """Облегчённый сериализатор для списков."""
    ram_gb = serializers.SerializerMethodField()

    class Meta:
        model = VirtualMachine
        fields = [
            'id', 'name', 'vcpus', 'ram_mb', 'ram_gb',
            'disk_gb', 'os_type', 'status', 'ip_address', 'created_at',
        ]

    def get_ram_gb(self, obj):
        return round(obj.ram_mb / 1024, 2)
