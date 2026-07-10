from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.db import transaction
from .models import User, Department, UserSession, AuditLog


class DepartmentSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(source='users.count', read_only=True)
    
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'title', 'middle_name', 'national_id', 'employee_number', 'phone_number',
            'alternate_phone', 'date_of_birth', 'profile_picture', 'role', 'role_display',
            'department', 'department_name', 'specialization', 'license_number',
            'years_of_experience', 'emergency_contact_name', 'emergency_contact_phone',
            'date_joined_organization', 'employment_type', 'is_active', 'is_online',
            'last_activity', 'receive_email_notifications', 'receive_sms_notifications',
            'receive_whatsapp_notifications', 'two_factor_enabled', 'date_joined',
            'last_login', 'password_changed_at'
        ]
        read_only_fields = ('id', 'employee_number', 'date_joined', 'last_login', 'password_changed_at')
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'confirm_password', 'first_name', 'last_name',
            'title', 'middle_name', 'national_id', 'phone_number', 'alternate_phone',
            'date_of_birth', 'role', 'department', 'specialization', 'license_number',
            'years_of_experience', 'emergency_contact_name', 'emergency_contact_phone',
            'date_joined_organization', 'employment_type'
        ]
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords don't match"})
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'title', 'middle_name', 'phone_number',
            'alternate_phone', 'date_of_birth', 'profile_picture', 'specialization',
            'license_number', 'years_of_experience', 'emergency_contact_name',
            'emergency_contact_phone', 'receive_email_notifications',
            'receive_sms_notifications', 'receive_whatsapp_notifications'
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name', 
                  'phone_number', 'role', 'employee_number', 'gender', 'date_of_birth']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Password fields didn't match."})
        
        # Prevent admin/super_admin registration through public registration
        if attrs.get('role') in ['admin', 'super_admin']:
            raise serializers.ValidationError({"role": "Admin accounts cannot be created through registration. Contact system administrator."})
        
        # Validate role is valid
        valid_roles = ['doctor', 'clinical_officer', 'nurse', 'lab_technician', 
                       'pharmacist', 'pharmacy_tech', 'records_officer', 'receptionist', 
                       'cashier', 'manager', 'viewer']
        if attrs.get('role') not in valid_roles:
            raise serializers.ValidationError({"role": f"Invalid role. Valid roles are: {', '.join(valid_roles)}"})
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()
        return user


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = '__all__'
        read_only_fields = ('id', 'login_time', 'last_activity')


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ('id', 'timestamp')
    
    def get_user_full_name(self, obj):
        if obj.user:
            return obj.user.get_full_name()
        return None


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_new_password = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "Passwords don't match"})
        
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({"old_password": "Wrong password"})
        
        return data


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)