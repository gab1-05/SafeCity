"""
Serializers for registration, login, profile and user management.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import ConsentRecord, Department, RoleRequest, User, UserRole
from apps.accounts.roles import REQUESTABLE_ROLES


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    accept_terms = serializers.BooleanField(write_only=True)
    # Optional elevated-role request. The account itself is always created
    # as `citizen`; a non-citizen value creates a pending RoleRequest for
    # admin approval instead of granting anything immediately.
    requested_role = serializers.ChoiceField(
        choices=UserRole.choices, required=False, allow_null=True, default=None
    )
    requested_department_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    role_request_reason = serializers.CharField(required=False, allow_blank=True, default="")

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
            "requested_role",
            "requested_department_id",
            "role_request_reason",
        ]

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("You must accept the terms to register.")
        return value

    def validate_requested_role(self, value):
        if value in (None, "", UserRole.CITIZEN):
            return None
        if value not in REQUESTABLE_ROLES:
            raise serializers.ValidationError(
                "That role cannot be requested. Contact an administrator."
            )
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):
        validated_data.pop("accept_terms")
        requested_role = validated_data.pop("requested_role", None)
        requested_department_id = validated_data.pop("requested_department_id", None)
        role_request_reason = validated_data.pop("role_request_reason", "")
        password = validated_data.pop("password")
        request = self.context.get("request")
        user = User.objects.create_user(**validated_data, password=password)
        ConsentRecord.objects.create(
            user=user,
            kind="terms",
            version="1.0",
            ip_address=request.META.get("REMOTE_ADDR") if request else None,
        )
        if requested_role:
            department = None
            if requested_department_id:
                department = Department.objects.filter(
                    pk=requested_department_id, is_active=True
                ).first()
            RoleRequest.objects.create(
                user=user,
                requested_role=requested_role,
                department=department,
                reason=role_request_reason or "",
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
            # No usable session yet: the caller must pass the second factor.
            # The view attaches a short-lived challenge token instead.
            data["requires_2fa"] = True
            data.pop("access", None)
            data.pop("refresh", None)
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
    # Accepts a 6-digit TOTP code *or* an 8-char recovery code (both flows
    # fall back to recovery codes, so the field must not be locked to 6 chars).
    token = serializers.CharField(min_length=6, max_length=64)


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


class RoleRequestSerializer(serializers.ModelSerializer):
    """Read serializer for role requests (admin queue + own requests)."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    current_role = serializers.CharField(source="user.role", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True, default=None)

    class Meta:
        model = RoleRequest
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "current_role",
            "requested_role",
            "department",
            "department_name",
            "reason",
            "status",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = fields


class RoleRequestCreateSerializer(serializers.Serializer):
    requested_role = serializers.ChoiceField(choices=UserRole.choices)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_requested_role(self, value):
        if value == UserRole.CITIZEN:
            raise serializers.ValidationError("You already have the citizen role.")
        if value not in REQUESTABLE_ROLES:
            raise serializers.ValidationError(
                "That role cannot be requested. Contact an administrator."
            )
        return value


class RoleRequestReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
