from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CompanyAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        company = self.user.company
        if company and not company.is_subscription_valid:
            raise PermissionDenied(
                "Kompaniya obunasi faol emas. Administrator bilan bog'laning."
            )

        if self.user.role == "cashier" and not self.user.is_subscription_valid:
            raise PermissionDenied(
                "Sizning ishchi obunangiz muddati tugagan. Administratoringiz bilan bog'laning."
            )

        return data
