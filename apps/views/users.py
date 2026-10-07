from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.conf import settings
from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.models import User, Markaz, Company, SubscriptionStatus, SubscriptionAuditLog, SubscriptionPayment, UserPlan
from apps.permissions import IsSuperAdmin
from apps.serializers import (
    UserCreateSerializer, UserSerializer, UserUpdateByAdminSerializer, MarkazSerializer, UserSubscriptionSerializer,
)
from drf_spectacular.utils import extend_schema


def get_subscription_response(user, extra=None):
    status_val = user.computed_status
    days = user.days_left
    end_date_str = user.subscription_expires_at.isoformat() if user.subscription_expires_at else None
    data = {
        "id": user.id,
        "plan": user.plan,
        "status": status_val,
        "subscriptionEndDate": end_date_str,
        "daysLeft": days,
    }
    if extra:
        data.update(extra)
        for k, v in list(extra.items()):
            if "_" in k:
                parts = k.split("_")
                cam_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
                data[cam_key] = v
    return data


@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    """Superadmin uchun: kassir yaratish/tahrirlash/o'chirish va obunani boshqarish."""
    queryset = User.objects.filter(role="cashier")
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return User.objects.filter(role="cashier", company=self.request.user.company)

    def create(self, request, *args, **kwargs):
        if not request.user or not request.user.company:
            return Response({"detail": "Avval administratorni kompaniyaga biriktiring."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        response_data = UserSerializer(user, context=self.get_serializer_context()).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        if not self.request.user.company:
            raise serializers.ValidationError({"detail": "Avval administratorni kompaniyaga biriktiring."})
        return serializer.save(company=self.request.user.company)

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateByAdminSerializer
        return UserSerializer

    @action(detail=True, methods=['put', 'patch', 'post'], url_path='subscription')
    def subscription(self, request, pk=None):
        user = self.get_object()
        serializer = UserSubscriptionSerializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        if new_status == SubscriptionStatus.ACTIVE:
            if not user.subscription_expires_at or user.subscription_expires_at < timezone.localdate():
                return Response({"detail": "Avval obuna ulang (renew-subscription)."}, status=status.HTTP_400_BAD_REQUEST)
        user.subscription_status = new_status
        user.save()
        SubscriptionAuditLog.objects.create(
            user=user, admin=request.user, 
            old_date=user.subscription_expires_at, new_date=user.subscription_expires_at, 
            action=f'subscription-status-{user.subscription_status}'
        )
        return Response(get_subscription_response(user), status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='renew-subscription')
    def renew_subscription(self, request, pk=None):
        user = self.get_object()
        months = request.data.get('months')
        try:
            months_int = int(months)
        except (TypeError, ValueError):
            return Response({"months": ["1, 3, 6 yoki 12 bo'lishi kerak."]}, status=400)
        
        if months_int not in [1, 3, 6, 12]:
            return Response({"months": ["1, 3, 6 yoki 12 bo'lishi kerak."]}, status=400)
        
        old_date = user.subscription_expires_at
        base_date = max(timezone.localdate(), user.subscription_expires_at or timezone.localdate())
        new_date = base_date + relativedelta(months=months_int)
        
        user.plan = UserPlan.STANDARD
        user.subscription_expires_at = new_date
        user.subscription_status = SubscriptionStatus.ACTIVE
        user.save()

        SubscriptionPayment.objects.create(
            user=user,
            admin=request.user,
            months=months_int,
            amount=months_int * settings.SUBSCRIPTION_PRICE_PER_MONTH,
            plan=UserPlan.STANDARD
        )

        SubscriptionAuditLog.objects.create(user=user, admin=request.user, old_date=old_date, new_date=new_date, action='renew')
        return Response(get_subscription_response(user))

    @action(detail=True, methods=['post'], url_path='subscription/set-date')
    def set_date(self, request, pk=None):
        user = self.get_object()
        if user.plan == UserPlan.FREE:
            return Response({"detail": "Bepul tarifdagi kassirga avval standart tarif ulang."}, status=status.HTTP_400_BAD_REQUEST)

        end_date_str = request.data.get('end_date')
        if not end_date_str:
            return Response({"end_date": ["Sana formati noto'g'ri (YYYY-MM-DD) yoki kiritilmadi."]}, status=400)
        try:
            parsed_date = datetime.strptime(str(end_date_str), "%Y-%m-%d").date()
        except ValueError:
            return Response({"end_date": ["Sana formati noto'g'ri (YYYY-MM-DD) formatda bo'lishi kerak."]}, status=400)
        
        today = timezone.localdate()
        if parsed_date < today:
            return Response({"end_date": ["O'tmishdagi sanani belgilash mumkin emas."]}, status=400)
        
        old_date = user.subscription_expires_at
        user.subscription_expires_at = parsed_date
        user.save()
        SubscriptionAuditLog.objects.create(user=user, admin=request.user, old_date=old_date, new_date=parsed_date, action='set-date')
        return Response(get_subscription_response(user))

    @action(detail=True, methods=['post'], url_path='subscription/shorten')
    def shorten(self, request, pk=None):
        user = self.get_object()
        if user.plan == UserPlan.FREE:
            return Response({"detail": "Bepul tarifdagi kassirga avval standart tarif ulang."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.subscription_expires_at:
            return Response({"detail": "Muddat belgilanmagan kassirni qisqartirib bo'lmaydi."}, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.localdate()
        if user.subscription_expires_at < today:
            return Response({"months": ["Muddati tugagan kassirni qisqartirib bo'lmaydi."]}, status=status.HTTP_400_BAD_REQUEST)

        months = request.data.get('months')
        try:
            months_int = int(months)
        except (TypeError, ValueError):
            return Response({"months": ["1, 3 yoki 6 bo'lishi kerak."]}, status=400)
        
        if months_int not in [1, 3, 6]:
            return Response({"months": ["1, 3 yoki 6 bo'lishi kerak."]}, status=400)
        
        old_date = user.subscription_expires_at
        current_end = user.subscription_expires_at
        new_date = current_end - relativedelta(months=months_int)
        clamped = False
        if new_date < today:
            new_date = today
            clamped = True
        
        user.subscription_expires_at = new_date
        user.save()
        SubscriptionAuditLog.objects.create(user=user, admin=request.user, old_date=old_date, new_date=new_date, action='shorten')
        return Response(get_subscription_response(user, {"clamped": clamped}))

    @action(detail=True, methods=['post'], url_path='deactivate-subscription')
    def deactivate_subscription(self, request, pk=None):
        user = self.get_object()
        old_date = user.subscription_expires_at
        user.subscription_status = SubscriptionStatus.INACTIVE
        user.save()
        SubscriptionAuditLog.objects.create(user=user, admin=request.user, old_date=old_date, new_date=old_date, action='deactivate')
        return Response(get_subscription_response(user))


@extend_schema(tags=["Tariffs"])
class TariffsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        tariffs = [
            {
                "code": "free",
                "name": "Bepul",
                "days": settings.FREE_TRIAL_DAYS,
                "price": 0
            },
            {
                "code": "standard",
                "name": "Standart",
                "pricePerMonth": settings.SUBSCRIPTION_PRICE_PER_MONTH
            }
        ]
        return Response(tariffs)


@extend_schema(tags=["Markazlar"])
class MarkazViewSet(viewsets.ModelViewSet):
    queryset = Markaz.objects.all()
    serializer_class = MarkazSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated or not user.company:
            return Markaz.objects.none()
        return Markaz.objects.filter(company=user.company)

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user or not user.is_authenticated or not user.company:
            return Response({"detail": "Avval administratorni kompaniyaga biriktiring."}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        if not user or not user.company:
            raise serializers.ValidationError({"detail": "Avval administratorni kompaniyaga biriktiring."})
        serializer.save(company=user.company)
