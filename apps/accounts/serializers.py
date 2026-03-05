from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from .models import User, Organization, OrganizationMembership, Client, Plan, OrganizationSubscription


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Подтверждение пароля')

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Пароли не совпадают.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'date_joined']
        read_only_fields = fields


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'description', 'is_active', 'member_count', 'created_at']
        read_only_fields = ['id', 'is_active', 'member_count', 'created_at']

    def get_member_count(self, obj):
        return obj.memberships.count()


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ['id', 'user', 'user_email', 'user_full_name', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at', 'user_email', 'user_full_name']

    def validate_role(self, value):
        # Только owner может назначить кого-то owner'ом
        request = self.context.get('request')
        if (value == OrganizationMembership.Role.OWNER
                and request
                and request.current_role != OrganizationMembership.Role.OWNER):
            raise serializers.ValidationError(
                'Только владелец организации может назначить другого владельца.'
            )
        return value


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=OrganizationMembership.Role.choices)

    def validate_email(self, value):
        try:
            self._user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('Пользователь с таким email не найден.')
        return value



class ClientSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = ['id', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'position', 'created_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'display_name', 'max_projects', 'max_users', 'max_storage_gb', 'monthly_price', 'annual_price']

class OrganizationSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.display_name')
    is_over_limit = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationSubscription
        fields = ['id', 'plan', 'plan_name', 'current_projects', 'current_users', 'current_storage_gb', 'is_active', 'expires_at', 'is_over_limit']
    
    def get_is_over_limit(self, obj):
        return obj.is_over_limit