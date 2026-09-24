from rest_framework import serializers
from apps.models import Settings

class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = '__all__'
        read_only_fields = ['company']
