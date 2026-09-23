import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.telegram import send_start_reply
from drf_spectacular.utils import extend_schema

WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")


@extend_schema(exclude=True)
class TelegramWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Telegram har bir so'rovga shu headerni qo'shadi (setWebhook'da secret_token bilan sozlaganda)
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
            return Response(status=403)

        update = request.data
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        if text == "/start" and chat_id:
            send_start_reply(chat_id)

        return Response(status=200)
