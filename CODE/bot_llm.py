import telebot
from telebot import types
import random

# ТВОЙ ТОКЕН БОТА - ЗАМЕНИ ЕГО!
BOT_TOKEN = "8523664920:AAENFx004lsLW_8Sgffenwu75-GE1xiKmE8"

bot = telebot.TeleBot(BOT_TOKEN)

# Для хранения состояний пользователей
user_states = {}

class CodeAssistant:
    def generate_code(self, task_description):
        """Генерация примеров кода по ключевым словам"""
        task_lower = task_description.lower()
        
        # Библиотека готовых примеров кода
        examples = {
            "бота": """
🤖 <b>Пример телеграм бота на Python:</b>

```python
import telebot
from telebot import types

# ТВОЙ ТОКЕН БОТА
bot = telebot.TeleBot("ТВОЙ_ТОКЕН_ЗДЕСЬ")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('👋 Привет')
    btn2 = types.KeyboardButton('ℹ️ Информация')
    btn3 = types.KeyboardButton('🎲 Рандомное число')
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(
        message.chat.id,
        "🤖 <b>Привет! Я твой первый бот!</b>\\nВыбери действие:",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
<b>Доступные команды:</b>
/start - Начать работу
/help - Помощь
/info - Информация

<b>Просто напиши мне что-нибудь!</b>
    """
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text == '👋 Привет':
        bot.send_message(message.chat.id, "😊 И тебе привет! Как дела?")
    elif message.text == 'ℹ️ Информация':
        bot.send_message(message.chat.id, "🔧 Этот бот создан на Python с помощью pyTelegramBotAPI")
    elif message.text == '🎲 Рандомное число':
        number = random.randint(1, 100)
        bot.send_message(message.chat.id, f"🎯 Твое случайное число: <b>{number}</b>", parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, f"✍️ Ты написал: <b>{message.text}</b>", parse_mode='HTML')

if __name__ == "__main__":
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)