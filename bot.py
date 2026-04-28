import telebot
from openai import OpenAI

TELEGRAM_TOKEN = "8619718901:AAEH7aGHIoXlWAFdXvVBsm9ahxItel2xG-E"
OPENAI_API_KEY = "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"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

def is_simple(text):
    text = text.lower()
    keywords = ["крыша", "течет", "трещин", "вентиляц"]
    return any(k in text for k in keywords)

def ai_answer(text):
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Ты помощник строительной компании. Кратко отвечай и задавай вопросы."},
            {"role": "user", "content": text}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    answer = ai_manager_answer(user_id, message.text)
    bot.send_message(user_id, answer)

    # 💸 БЕЗ AI (бесплатно)
    if "крыша" in text or "течет" in text:
        bot.send_message(message.chat.id,
            "Проблема с кровлей.\n\n"
            "Пришлите:\n1. Фото\n2. Адрес\n3. Когда началось"
        )

    elif "трещин" in text:
        bot.send_message(message.chat.id,
            "Опишите трещины:\n1. Где\n2. Размер\n3. Фото"
        )

    # 🤖 AI только если непонятно
    else:
        bot.send_message(user_id, "Бот работает (AI временно отключен)")
        bot.send_message(message.chat.id, answer)

print("Бот запущен")

try:
    bot.polling(non_stop=True)
except Exception as e:
    print("ОШИБКА:")
    print(e)
