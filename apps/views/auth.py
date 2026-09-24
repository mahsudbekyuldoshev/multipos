from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.serializers.auth import CompanyAwareTokenObtainPairSerializer


@extend_schema(tags=["Auth"])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CompanyAwareTokenObtainPairSerializer


@extend_schema(tags=["Auth"])
class CustomTokenRefreshView(TokenRefreshView):
    pass
