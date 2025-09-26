import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError, BadRequest, TimedOut
from typing import Optional

# Загрузка переменных из .env файла
from dotenv import load_dotenv
load_dotenv()

# Безопасное получение токена
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set or empty")

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@alekseevdesignwb").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002408689600").strip()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

subscription_cache = {}

async def is_subscribed(user_id: int, app) -> bool:
    """Проверяет подписку пользователя на канал"""
    if user_id in subscription_cache:
        return subscription_cache[user_id]
    
    try:
        member = await app.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
        subscription_cache[user_id] = is_member
        return is_member
    except TelegramError as e:
        logger.warning(f"Ошибка проверки по username: {e}")
    
    try:
        member = await app.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
        subscription_cache[user_id] = is_member
        return is_member
    except TelegramError as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

def create_subscription_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("🔁 Проверить подписку", callback_data="check_subscription")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_welcome_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Отправляет приветственное фото"""
    try:
        possible_filenames = ['Бот баннер.png', 'bot_banner.png', 'welcome.png']
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        photo_path = None
        
        for filename in possible_filenames:
            file_path = os.path.join(current_dir, filename)
            if os.path.exists(file_path):
                photo_path = file_path
                break
        
        if photo_path:
            with open(photo_path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption="🎉 **Добро пожаловать!**\n\nДля доступа подпишитесь на наш канал.",
                    parse_mode='Markdown'
                )
            return True
        else:
            await update.message.reply_text(
                "🎉 **Добро пожаловать!**\n\nДля доступа подпишитесь на наш канал.",
                parse_mode='Markdown'
            )
            return False
    except Exception as e:
        logger.error(f"Ошибка при отправке фото: {e}")
        await update.message.reply_text("🎉 Добро пожаловать!")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    logger.info(f"Start от пользователя {user_id}")
    
    try:
        await send_welcome_photo(update, context)
        
        if await is_subscribed(user_id, context.application):
            await update.message.reply_text(f"✅ Привет, {user_name}! Доступ разрешен.")
        else:
            await update.message.reply_text(
                f"❌ Подпишитесь на канал {CHANNEL_USERNAME}.",
                reply_markup=create_subscription_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        await update.message.reply_text("⚠️ Ошибка. Попробуйте позже.")

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    if user_id in subscription_cache:
        del subscription_cache[user_id]
    
    try:
        if await is_subscribed(user_id, context.application):
            await query.edit_message_text(f"✅ Привет, {user_name}! Доступ разрешен.")
        else:
            await query.edit_message_text(
                f"❌ Вы не подписаны на канал {CHANNEL_USERNAME}!",
                reply_markup=create_subscription_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await query.message.reply_text("⚠️ Ошибка проверки.")

async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Ошибка: {context.error}")

def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return

    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))
        application.add_error_handler(error_handler)
        
        logger.info("Бот запускается...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")

if __name__ == "__main__":
    main()