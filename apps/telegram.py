import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text, reply_markup=None):
    """Best-effort yuborish — xato bo'lsa, chaqiruvchi kodni buzmaydi."""
    try:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        r = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=5)
        return r.ok
    except requests.RequestException:
        return False


def notify_admin_new_contact(contact):
    text = (
        f"🔔 <b>Yangi murojaat</b>\n\n"
        f"👤 Ism: {contact.name}\n"
        f"📞 Tel: {contact.phone}\n"
        f"💬 Xabar: {contact.message}"
    )
    send_message(ADMIN_CHAT_ID, text)


def send_start_reply(chat_id):
    text = (
        "👋 <b>MultiPOS</b> — ko'p sohali savdo va ombor boshqaruv tizimi.\n\n"
        "Qurilish, elektrika, santexnika va avto ehtiyot qismlari do'konlari uchun "
        "kassa va ombor nazorati.\n\n"
        "Batafsil ma'lumot uchun saytimizga o'ting 👇"
    )
    reply_markup = {
        "inline_keyboard": [[
            {"text": "🌐 Saytga o'tish", "url": "https://multipos.uz"}
        ]]
    }
    send_message(chat_id, text, reply_markup)
