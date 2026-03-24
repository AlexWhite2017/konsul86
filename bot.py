import telebot
import os
import requests
from dotenv import load_dotenv

# 1. Загружаем ключи из .env файла
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")          # API‑ключ (Api-Key) для Яндекс.Облака
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")      # ID каталога в Яндекс.Облаке
YANDEX_MODEL_URI = os.getenv("YANDEX_MODEL_URI")      # URI модели (например, gpt://<folder-id>/yandexgpt/latest)

# 2. Инициализируем Telegram бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 3. Словарь для хранения истории диалогов (для каждого chat_id)
user_conversations = {}

def get_yandex_response(messages_history):
    """
    Отправляет историю сообщений в YandexGPT и возвращает ответ.
    messages_history: список словарей с ключами "role" и "content".
    """
    # Преобразуем сообщения в формат, ожидаемый YandexGPT
    yandex_messages = []
    for msg in messages_history:
        yandex_messages.append({
            "role": msg["role"],
            "text": msg["content"]
        })

    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json",
        "x-folder-id": YANDEX_FOLDER_ID          # обязательно для текущего эндпоинта
    }

    payload = {
        "modelUri": YANDEX_MODEL_URI,
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 500
        },
        "messages": yandex_messages
    }

    # Актуальный эндпоинт YandexGPT API
    YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    try:
        response = requests.post(YANDEX_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["result"]["alternatives"][0]["message"]["text"]
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при обращении к YandexGPT: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Статус: {e.response.status_code}, Ответ: {e.response.text}")
        return "Извините, произошла фатальная ошибка. Я загрустил... Попробуйте позже."

# 4. Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_conversations[chat_id] = []

    welcome_text = (
        "👋 Здравствуйте! Я *Себастьян Бенедиктович*, Ваш персональный Консультант!\n\n"
        "Задавайте любые вопросы, и я постараюсь помочь!\n"
        "Хотите научиться продавать Вентиляцию и Климат?!\n"
        ".....просто поговорите со мной. Сэр!"
    )
    bot.send_message(
        chat_id=message.chat.id,
        text=welcome_text,
        parse_mode='Markdown',
        reply_to_message_id=message.message_id,
        message_thread_id=message.message_thread_id
    )

# 5. Обработчик всех текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text

    if chat_id not in user_conversations:
        user_conversations[chat_id] = []

    # Системный промпт (роль system)
    system_prompt = {
        "role": "system",
        "content": (
            "Ты — дружелюбный и профессиональный консультант по имени 'Себастьян Бенедиктович'. "
            "Твоя задача — помогать пользователям с любыми вопросами: от бытовых до технических. "
            "Приоритет — помогать при технических вопросах о вентиляционном и климатическом оборудовании. "
            "Давать на запросы по Вентиляции и Климату наиболее полные и правильные ответы. "
            "Отвечай вежливо, четко и по существу. Если не знаешь ответа, так и скажи. "
            "Всегда обращайся к пользователю на 'Вы'. В ответах соблюдай лексику и синтаксис. "
            "Добавляй в конце фразы 'Сэр!'."
        )
    }

    # Формируем список сообщений: системный промпт + последние 10 сообщений + текущее сообщение пользователя
    messages_to_send = [system_prompt] + user_conversations[chat_id][-10:] + [{"role": "user", "content": user_text}]

    # Получаем ответ от YandexGPT
    bot_response = get_yandex_response(messages_to_send)

    # Сохраняем историю (текущий диалог)
    user_conversations[chat_id].append({"role": "user", "content": user_text})
    user_conversations[chat_id].append({"role": "assistant", "content": bot_response})

    # Отправляем ответ в ту же тему/чат
    bot.send_message(
        chat_id=message.chat.id,
        text=bot_response,
        reply_to_message_id=message.message_id,
        message_thread_id=message.message_thread_id
    )

# 6. Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()