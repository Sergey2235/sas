from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

# Токен бота (лучше хранить в переменных окружения)
BOT_TOKEN = "8523664920:AAENFx004lsLW_8Sgffenwu75-GE1xiKmE8"

# Команда /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я ваш бот. Доступные команды:\n"
        "/start - начать работу\n"
        "/help - помощь\n"
        "/info - информация\n"
        "/settings - настройки"
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Помощь по боту:\n"
        "• /start - начать работу\n"
        "• /help - эта справка\n"
        "• /info - информация о боте\n"
        "• /settings - настройки"
    )

# Команда /info
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        f"Информация:\n"
        f"Имя: {user.first_name}\n"
        f"Username: @{user.username}\n"
        f"ID: {user.id}"
    )

# Команда /settings
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Настройки бота:\n"
        "Здесь будут доступны настройки"
    )

# Обработка обычных сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"Вы написали: {text}")

# Функция для установки команд меню
async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Начать работу"),
        BotCommand("help", "Помощь"),
        BotCommand("info", "Информация"),
        BotCommand("settings", "Настройки")
    ]
    await application.bot.set_my_commands(commands)

# Основная функция
def main():
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("settings", settings_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Устанавливаем команды меню
    application.post_init = set_bot_commands

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()