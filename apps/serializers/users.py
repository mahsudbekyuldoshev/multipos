from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.models import User, Markaz


class MarkazSerializer(serializers.ModelSerializer):
    class Meta:
        model = Markaz
        fields = ["id", "name", "address"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "phone_number", "first_name", "last_name", "markaz", "password"]

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
        fields = ["id", "phone_number", "first_name", "last_name", "role", "markaz", "is_active"]


class UserUpdateByAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = User
        fields = ["phone_number", "first_name", "last_name", "markaz", "is_active", "password"]

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
