"""
Serializers for registration, login, profile and user management.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import ConsentRecord, Department, User, UserRole


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    accept_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "accept_terms",
            "prefers_anonymous_reporting",
        ]

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("You must accept the terms to register.")
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):
        validated_data.pop("accept_terms")
        password = validated_data.pop("password")
        request = self.context.get("request")
        user = User.objects.create_user(**validated_data, password=password)
        ConsentRecord.objects.create(
            user=user,
            kind="terms",
            version="1.0",
            ip_address=request.META.get("REMOTE_ADDR") if request else None,
        )
        return user


class SafeCityTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login serializer adding role/department claims and enforcing lockout."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["department_id"] = str(user.department_id) if user.department_id else None
        token["2fa_enabled"] = user.two_factor_enabled
        return token

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs.get(self.username_field)).first()
        if (
            user
            and user.locked_until
            and user.locked_until > __import__("django").utils.timezone.now()
        ):
            raise serializers.ValidationError(
                {
                    "detail": "Account temporarily locked due to failed login attempts.",
                    "code": "account_locked",
                },
                code="account_locked",
            )
        data = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.id),
            "email": self.user.email,
            "role": self.user.role,
            "full_name": self.user.full_name,
        }
        if self.user.two_factor_enabled:
            data["requires_2fa"] = True
        return data


class MeSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "department",
            "prefers_anonymous_reporting",
            "language",
            "email_verified_at",
            "two_factor_enabled",
        ]

    def get_department(self, obj):
        if obj.department:
            return {
                "id": str(obj.department.id),
                "name": obj.department.name,
                "code": obj.department.code,
            }
        return None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "prefers_anonymous_reporting", "language"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class TwoFactorSetupSerializer(serializers.Serializer):
    pass


class TwoFactorVerifySerializer(serializers.Serializer):
    token = serializers.CharField(min_length=6, max_length=6)


class DepartmentSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "code",
            "description",
            "contact_email",
            "contact_phone",
            "is_emergency_department",
            "is_active",
            "member_count",
        ]


class UserManagementSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "department",
            "is_active",
            "is_locked",
            "locked_until",
            "created_at",
        ]

    def get_department(self, obj):
        if obj.department:
            return {"id": str(obj.department.id), "name": obj.department.name}
        return None

    def get_is_locked(self, obj):
        return bool(obj.locked_until and obj.locked_until > __import__("django").utils.timezone.now())


class UserRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=UserRole.choices)
    department_id = serializers.UUIDField(required=False, allow_null=True)
