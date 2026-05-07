import os
import time
import threading
import traceback

import telebot
from openai import OpenAI
from flask import Flask


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_TOKEN в Render Environment Variables")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

users = {}

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running"


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
- не давать окончательных технических заключений.

Обязательно собери:
1. Имя
2. Телефон
3. Адрес объекта
4. Тип объекта
5. Описание проблемы
6. Фото/документы, если есть
7. Что нужно: консультация, обследование, проект или смета

Задавай 1-2 вопроса за раз.
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
    answer = ai_manager_answer(user_id, message.text)
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

    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
