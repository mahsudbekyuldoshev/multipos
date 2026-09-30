from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.models import User, Markaz


class MarkazSerializer(serializers.ModelSerializer):
    class Meta:
        model = Markaz
        fields = ["id", "name", "address"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    subscription_status = serializers.ChoiceField(choices=["active", "inactive"], required=False)
    subscription_expires_at = serializers.DateField(required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "first_name",
            "last_name",
            "markaz",
            "password",
            "subscription_status",
            "subscription_expires_at",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data, role="cashier")
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    markaz = MarkazSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "first_name",
            "last_name",
            "role",
            "markaz",
            "is_active",
            "subscription_status",
            "subscription_expires_at",
        ]


class UserSubscriptionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["active", "inactive"], required=False)
    expires_at = serializers.DateField(required=False, allow_null=True)
    expiresAt = serializers.DateField(required=False, allow_null=True)
    months = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if "expires_at" not in attrs and "expiresAt" not in attrs and "months" not in attrs and "status" not in attrs:
            raise serializers.ValidationError({
                "status": ["Ushbu maydon talab qilinadi."],
                "expiresAt": ["Ushbu maydon talab qilinadi."],
                "months": ["Ushbu maydon talab qilinadi."]
            })
        if "months" in attrs and attrs["months"] is not None:
            months = int(attrs["months"])
            # Always calculate from today, overwriting old expiration date rather than accumulating
            attrs["expires_at"] = timezone.now().date() + relativedelta(months=months)
        elif "expires_at" not in attrs and "expiresAt" in attrs:
            attrs["expires_at"] = attrs["expiresAt"]
        return attrs


class UserUpdateByAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = User
        fields = [
            "phone_number",
            "first_name",
            "last_name",
            "markaz",
            "is_active",
            "password",
            "subscription_status",
            "subscription_expires_at",
        ]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance


class ProfileSerializer(serializers.ModelSerializer):
    markaz = MarkazSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "phone_number", "first_name", "last_name", "role", "markaz"]
        read_only_fields = ["first_name", "last_name", "role", "markaz"]


class ProfileUpdateSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False)
    old_password = serializers.CharField(required=False, write_only=True)
    new_password = serializers.CharField(required=False, write_only=True, validators=[validate_password])

    def validate(self, data):
        if data.get("new_password") and not data.get("old_password"):
            raise serializers.ValidationError("Yangi parol kiritilganda joriy parol ham talab qilinadi.")
        return data
