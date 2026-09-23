from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.views.auth import CustomTokenObtainPairView, CustomTokenRefreshView

urlpatterns = (
    [
        path('', RedirectView.as_view(url='/api/docs/', permanent=False)),
        path('api/token/', CustomTokenObtainPairView.as_view()),
        path('api/token/refresh/', CustomTokenRefreshView.as_view()),
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
        path("admin/", admin.site.urls),
        path("api/v1/", include("apps.urls")),
    ]
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
)
