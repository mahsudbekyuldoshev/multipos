from rest_framework import serializers
from apps.models import Category
from django.utils.text import slugify


class CategorySerializer(serializers.ModelSerializer):
    key = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Category
        fields = ["key", "label", "icon", "accent"]

    def validate_key(self, value):
        if value and Category.objects.filter(key=value).exists():
            raise serializers.ValidationError("Bu qiymat band.")
        return value

    def create(self, validated_data):
        label = validated_data.get("label")
        key = validated_data.get("key")
        if not key:
            candidate_key = slugify(label)
            # Ensure uniqueness if slugified key exists
            base_key = candidate_key
            counter = 1
            while Category.objects.filter(key=candidate_key).exists():
                candidate_key = f"{base_key}-{counter}"
                counter += 1
            validated_data["key"] = candidate_key
        return super().create(validated_data)
