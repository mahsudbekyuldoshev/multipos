from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.models import Contact
from apps.serializers import ContactSerializer
from apps.telegram import notify_admin_new_contact
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Contact"])
class ContactCreateView(APIView):
    # Diqqat: bu ochiq forma, login talab qilmaydi
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Ma'lumotlar to'liq emas yoki noto'g'ri."}, status=400)

        contact = serializer.save(
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )

        # Telegramga bildirishnoma — muvaffaqiyatsiz bo'lsa ham forma 201 qaytaradi
        notify_admin_new_contact(contact)

        return Response(ContactSerializer(contact).data, status=201)
