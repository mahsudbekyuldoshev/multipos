from rest_framework.views import APIView
from rest_framework.response import Response
from apps.models import Settings
from apps.serializers import SettingsSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Settings"])
class SettingsView(APIView):
    def get(self, request):
        settings, _ = Settings.objects.get_or_create(company=request.user.company)
        return Response(SettingsSerializer(settings).data)

    def put(self, request):
        settings, _ = Settings.objects.get_or_create(company=request.user.company)
        serializer = SettingsSerializer(settings, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
