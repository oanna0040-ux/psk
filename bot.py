import os
import time
import json
import threading
import traceback
from datetime import datetime

import telebot
import gspread
from flask import Flask
from openai import OpenAI
from google.oauth2.service_account import Credentials


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")


if not TELEGRAM_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_TOKEN в Render Environment Variables")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

users = {}

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running"


def get_sheet():
    if not GOOGLE_SHEET_ID:
        print("Не найден GOOGLE_SHEET_ID")
        return None

    if not GOOGLE_CREDENTIALS_JSON:
        print("Не найден GOOGLE_CREDENTIALS_JSON")
        return None

    credentials_info = json.loads(GOOGLE_CREDENTIALS_JSON)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets"
    ]

    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )

    gs_client = gspread.authorize(credentials)
    return gs_client.open_by_key(GOOGLE_SHEET_ID)


def save_dialog_message(user_id, username, role, text):
    try:
        sheet = get_sheet()
        if sheet is None:
            return

        worksheet = sheet.worksheet("Диалоги")

        worksheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(user_id),
            username or "",
            role,
            text
        ])

    except Exception as e:
        print("GOOGLE SHEETS ERROR save_dialog_message:")
        print(e)
        traceback.print_exc()


def save_lead(user_id, username, category="", name="", phone="", address="", object_type="", description="", need="", summary=""):
    try:
        sheet = get_sheet()
        if sheet is None:
            return

        worksheet = sheet.worksheet("Заявки")

        worksheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(user_id),
            username or "",
            category,
            name,
            phone,
            address,
            object_type,
            description,
            need,
            "Новая",
            summary
        ])

    except Exception as e:
        print("GOOGLE SHEETS ERROR save_lead:")
        print(e)
        traceback.print_exc()


def ai_manager_answer(user_id, user_text):
    if not client:
        return "AI пока не подключён. Проверьте OPENAI_API_KEY в Render."

    history = users.get(user_id, [])

    messages = [
        {
            "role": "system",
            "content": """
Ты менеджер строительной проектной компании.

Веди клиента пошагово, кратко и вежливо.

Твоя задача:
- понять проблему клиента;
- задать уточняющие вопросы;
- собрать заявку;
- не давать окончательных технических заключений;
- не обещать точную стоимость без анализа документов.

Обязательно постепенно собери:
1. Имя клиента
2. Телефон
3. Адрес объекта
4. Тип объекта
5. Описание проблемы
6. Фото/документы, если есть
7. Что нужно: консультация, обследование, проект или смета

Если тема вентиляции:
попроси планы помещений, фото существующей системы, что требуется: замена, проектирование или обследование.

Если тема кровли:
попроси фото протечки, адрес, план БТИ/поэтажный план, когда появилась проблема.

Если тема трещин:
попроси фото, этаж, место трещины, когда появилась.

Задавай 1-2 вопроса за раз.
Отвечай как живой менеджер.
"""
        }
    ]

    messages += history
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=250
        )

        answer = response.choices[0].message.content

        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": answer})
        users[user_id] = history[-12:]

        return answer

    except Exception as e:
        print("OPENAI ERROR:")
        print(e)
        traceback.print_exc()
        return "Сейчас AI временно недоступен. Мы получили ваше сообщение, специалист свяжется с вами позже."


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    username = message.from_user.username

    save_dialog_message(user_id, username, "client", message.text)

    answer = ai_manager_answer(user_id, message.text)

    save_dialog_message(user_id, username, "bot", answer)

    bot.send_message(user_id, answer)


def run_bot():
    print("Telegram bot polling started")

    while True:
        try:
            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=20,
                skip_pending=True
            )
        except Exception as e:
            print("TELEGRAM ERROR:")
            print(e)
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    print("Бот запускается")
    print("TELEGRAM_TOKEN:", "есть" if TELEGRAM_TOKEN else "нет")
    print("OPENAI_API_KEY:", "есть" if OPENAI_API_KEY else "нет")
    print("GOOGLE_SHEET_ID:", "есть" if GOOGLE_SHEET_ID else "нет")
    print("GOOGLE_CREDENTIALS_JSON:", "есть" if GOOGLE_CREDENTIALS_JSON else "нет")

    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
