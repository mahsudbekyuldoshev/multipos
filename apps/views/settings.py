from rest_framework.views import APIView
from rest_framework.response import Response
from apps.models import Settings
from apps.serializers import SettingsSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Settings"])
class SettingsView(APIView):
    def get(self, request):
        settings = Settings.objects.first() or Settings.objects.create()
        return Response(SettingsSerializer(settings).data)

    def put(self, request):
        settings = Settings.objects.first() or Settings.objects.create()
        serializer = SettingsSerializer(settings, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
