from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CompanyAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        company = self.user.company
        if company and not company.is_subscription_valid:
            raise PermissionDenied(
                "Obunangiz to'xtatilgan yoki muddati tugagan. Administrator bilan bog'laning."
            )
        return data
