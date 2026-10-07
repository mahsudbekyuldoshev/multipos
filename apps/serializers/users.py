import re
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from dateutil.relativedelta import relativedelta
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.models import User, Markaz, SubscriptionStatus, UserPlan, FreeTrialUsage, SubscriptionPayment, SubscriptionAuditLog


def normalize_phone(value):
    if not value:
        return ""
    digits = re.sub(r'\D', '', str(value))
    if len(digits) == 9:
        digits = "998" + digits
    return digits


from rest_framework.validators import UniqueValidator


class PhoneField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 20)
        validators = kwargs.pop('validators', [])
        validators.append(UniqueValidator(queryset=User.objects.all(), message="Bu telefon raqami allaqachon mavjud."))
        kwargs['validators'] = validators
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        val = super().to_internal_value(data)
        return normalize_phone(val)


class MarkazSerializer(serializers.ModelSerializer):
    class Meta:
        model = Markaz
        fields = ["id", "name", "address"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    phone_number = PhoneField()
    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    plan = serializers.ChoiceField(choices=[UserPlan.FREE, UserPlan.STANDARD], required=False, default=UserPlan.FREE)
    subscription_months = serializers.ChoiceField(choices=[1, 3, 6, 12], required=False, allow_null=True, write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "first_name",
            "last_name",
            "markaz",
            "password",
            "plan",
            "subscription_months",
        ]

    def validate(self, attrs):
        plan = attrs.get('plan', UserPlan.FREE)
        phone = attrs.get('phone_number')
        months = attrs.get('subscription_months')

        if plan == UserPlan.FREE:
            if phone and FreeTrialUsage.objects.filter(phone_number=phone).exists():
                raise serializers.ValidationError({
                    "plan": ["Bu raqam bepul davrdan foydalangan. Standart tarifni tanlang."]
                })
        elif plan == UserPlan.STANDARD:
            if not months or months not in [1, 3, 6, 12]:
                raise serializers.ValidationError({
                    "subscription_months": ["Standart tarif uchun oy miqdori (1, 3, 6 yoki 12) majburiy."]
                })
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        plan = validated_data.pop("plan", UserPlan.FREE)
        months = validated_data.pop("subscription_months", None)
        phone = validated_data.get("phone_number", "")
        request = self.context.get('request')
        admin = request.user if request and request.user and request.user.is_authenticated else None

        with transaction.atomic():
            today = timezone.localdate()
            if plan == UserPlan.FREE:
                expires_at = today + timedelta(days=settings.FREE_TRIAL_DAYS)
                sub_status = SubscriptionStatus.ACTIVE
            else:
                expires_at = today + relativedelta(months=int(months))
                sub_status = SubscriptionStatus.ACTIVE

            user = User(
                **validated_data,
                role="cashier",
                plan=plan,
                subscription_status=sub_status,
                subscription_expires_at=expires_at,
            )
            if password:
                user.set_password(password)
            user.save()

            if phone:
                FreeTrialUsage.objects.get_or_create(phone_number=phone)

            if plan == UserPlan.STANDARD and months:
                months_int = int(months)
                SubscriptionPayment.objects.create(
                    user=user,
                    admin=admin,
                    months=months_int,
                    amount=months_int * settings.SUBSCRIPTION_PRICE_PER_MONTH,
                    plan=UserPlan.STANDARD
                )
                SubscriptionAuditLog.objects.create(
                    user=user,
                    admin=admin,
                    old_date=None,
                    new_date=expires_at,
                    action='create'
                )

        return user


class UserSerializer(serializers.ModelSerializer):
    markaz = MarkazSerializer(read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    status = serializers.CharField(source="computed_status", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "first_name",
            "last_name",
            "role",
            "plan",
            "markaz",
            "is_active",
            "subscription_status",
            "subscription_expires_at",
            "status",
            "days_left",
        ]


class UserSubscriptionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["active", "inactive"])

    def validate(self, attrs):
        request_data = self.initial_data
        if "expires_at" in request_data or "expiresAt" in request_data or "months" in request_data:
            raise serializers.ValidationError({
                "detail": "Muddatni o'zgartirish uchun renew, set-date yoki shorten dan foydalaning."
            })
        return attrs


class UserUpdateByAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    phone_number = PhoneField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            "phone_number",
            "first_name",
            "last_name",
            "markaz",
            "is_active",
            "password",
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
