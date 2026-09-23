from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.views import ProductViewSet, SaleViewSet, SettingsView, CategoryListView, UserViewSet, MarkazViewSet, ProfileView, ContactCreateView, TelegramWebhookView

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'sales', SaleViewSet)
router.register(r'users', UserViewSet)
router.register(r'markazlar', MarkazViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('settings/', SettingsView.as_view()),
    path('categories/', CategoryListView.as_view()),
    path('profile/', ProfileView.as_view()),
    path('contact/', ContactCreateView.as_view()),
    path('telegram/webhook/', TelegramWebhookView.as_view()),
]
