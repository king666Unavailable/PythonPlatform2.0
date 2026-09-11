"""Shared API serializers."""

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Validate the temporary login request."""

    username = serializers.CharField(max_length=64, trim_whitespace=True)
    password = serializers.CharField(max_length=128, write_only=True, allow_blank=False, trim_whitespace=False)

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("\u7528\u6237\u540d\u4e0d\u80fd\u4e3a\u7a7a\u3002")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Validate a student's self-service password change request."""

    username = serializers.CharField(max_length=64, trim_whitespace=True)
    old_password = serializers.CharField(max_length=128, write_only=True, allow_blank=False, trim_whitespace=False)
    new_password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True,
        allow_blank=False,
        trim_whitespace=False,
    )
    confirm_password = serializers.CharField(max_length=128, write_only=True, allow_blank=False, trim_whitespace=False)

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("\u7528\u6237\u540d\u4e0d\u80fd\u4e3a\u7a7a\u3002")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "\u4e24\u6b21\u8f93\u5165\u7684\u65b0\u5bc6\u7801\u4e0d\u4e00\u81f4\u3002"})
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "\u65b0\u5bc6\u7801\u4e0d\u80fd\u4e0e\u539f\u5bc6\u7801\u76f8\u540c\u3002"})
        return attrs
