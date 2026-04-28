import os
import telebot
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("8619718901:AAEH7aGHIoXlWAFdXvVBsm9ahxItel2xG-E")
OPENAI_API_KEY = os.getenv("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")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

users = {}

def ai_manager_answer(user_id, user_text):
    history = users.get(user_id, [])

    messages = [
        {
            "role": "system",
            "content": """
Ты менеджер строительной проектной компании.
Веди клиента пошагово, кратко и вежливо.

Собери:
1. Имя
2. Телефон
3. Адрес объекта
4. Тип объекта
5. Описание проблемы
6. Фото/документы, если есть
7. Что нужно: консультация, обследование, проект или смета

Не давай окончательных технических заключений.
Задавай 1-2 вопроса за раз.
"""
        }
    ]

    messages += history
    messages.append({"role": "user", "content": user_text})

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


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    answer = ai_manager_answer(user_id, message.text)
    bot.send_message(user_id, answer)


print("Бот запущен")
bot.polling(non_stop=True)
