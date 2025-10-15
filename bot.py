import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# Проверка токена
TOKEN = os.environ.get("BOT_TOKEN")
REF_LINK = "https://www.tbank.ru/baf/7Yzkluz5kaS"  # ЗАМЕНИТЕ НА ВАШУ ССЫЛКУ
SUPPORT_USERNAME = "@otututu"  # ЗАМЕНИТЕ НА ВАШ USERNAME

# Проверка наличия токена
if not TOKEN:
    logging.error("❌ BOT_TOKEN не найден в переменных окружения!")
    logging.error("Пожалуйста, установите переменную BOT_TOKEN в настройках Railway")
    exit(1)
else:
    logging.info(f"✅ Токен получен. Длина: {len(TOKEN)} символов")

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я помогаю получить 1000 рублей за оформление карты T-Bank Black.

💰 *Как это работает:*
• Ты получаешь 500₽ от банка за оформление карты
• Плюс 500₽ от меня после первой покупки
• Итого: 1000₽ на руки!

📋 *Прежде чем начать, ознакомься с условиями нашего сотрудничества:*
    """
    
    keyboard = [
        [InlineKeyboardButton("📄 Показать условия", callback_data='show_terms')],
        [InlineKeyboardButton("💬 Поддержка", url=f'https://t.me/{SUPPORT_USERNAME[1:]}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_terms(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    terms_text = """
*✅ Условия сотрудничества и конфиденциальности*

*Нажимая «Я согласен», вы подтверждаете, что:*

🔒 *Политика конфиденциальности:*
• Мы НЕ передаем ваши личные данные третьим лицам
• Мы НЕ используем вашу информацию в корыстных целях
• Ваш username и реквизиты для выплаты используются ИСКЛЮЧИТЕЛЬНО для учета выплат
• Все данные удаляются после завершения наших обязательств

📋 *Условия сотрудничества:*
1. Вы действуете полностью добровольно, без принуждения
2. Вы ознакомились с официальными условиями акции банка
3. Вы понимаете схему вознаграждений (1000₽ вам, 2500₽ мне)
4. Вы осознаете, что это частная инициатива, а не предложение банка
5. Выполнение моих обязательств зависит от успешного зачисления бонуса от банка

💡 *Честное партнерство, где каждый получает свою выгоду в рамках акции банка.*
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Я согласен со всеми условиями", callback_data='get_link')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(terms_text, reply_markup=reply_markup, parse_mode='Markdown')

async def get_link(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    instruction_text = f"""
🎉 Отлично! Вот ваша ссылка для оформления:

{REF_LINK}

📝 *Инструкция:*
1. *Оформите карту* по ссылке выше
2. *Совершите покупку* от 500₽ (НЕ: ЖКХ, связь, переводы)
3. *Пришлите скриншот* подтверждения покупки в этот чат
4. *Получите 500₽* от меня в течение 24 часов после проверки

⚠️ *Важно:* карта должна быть оформлена именно по этой ссылке!
    """
    
    keyboard = [
        [InlineKeyboardButton("📱 Я оформил карту и совершил покупку", callback_data='instruction')],
        [InlineKeyboardButton("💬 Поддержка", url=f'https://t.me/{SUPPORT_USERNAME[1:]}')],
        [InlineKeyboardButton("🔙 Назад", callback_data='show_terms')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(instruction_text, reply_markup=reply_markup, parse_mode='Markdown')

async def instruction(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    instruction_text = """
📸 *Для получения 500₽ пришлите сюда:*
1. *Скриншот* из приложения банка, подтверждающий покупку
2. *Ваши реквизиты* для перевода (номер карты/телефона)

🕐 *Выплата производится в течение 24 часов* после проверки.

❓ *Что должно быть видно на скриншоте:*
- Дата и время операции
- Сумма покупки (от 500₽)
- Не видно конфиденциальных данных (замажьте CVV, полный номер карты)
    """
    
    keyboard = [
        [InlineKeyboardButton("💬 Поддержка", url=f'https://t.me/{SUPPORT_USERNAME[1:]}')],
        [InlineKeyboardButton("🔙 Назад", callback_data='get_link')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(instruction_text, reply_markup=reply_markup, parse_mode='Markdown')

async def back_to_start(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    # Пересоздаем сообщение с начальным меню
    user = query.from_user
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я помогаю получить 1000 рублей за оформление карты T-Bank Black.

💰 *Как это работает:*
• Ты получаешь 500₽ от банка за оформление карты
• Плюс 500₽ от меня после первой покупки
• Итого: 1000₽ на руки!

📋 *Прежде чем начать, ознакомься с условиями нашего сотрудничества:*
    """
    
    keyboard = [
        [InlineKeyboardButton("📄 Показать условия", callback_data='show_terms')],
        [InlineKeyboardButton("💬 Поддержка", url=f'https://t.me/{SUPPORT_USERNAME[1:]}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def main() -> None:
    try:
        logging.info("🚀 Запуск бота...")
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(show_terms, pattern='show_terms'))
        application.add_handler(CallbackQueryHandler(get_link, pattern='get_link'))
        application.add_handler(CallbackQueryHandler(instruction, pattern='instruction'))
        application.add_handler(CallbackQueryHandler(back_to_start, pattern='back_to_start'))
        
        logging.info("✅ Бот успешно запущен и ожидает сообщений")
        application.run_polling()
        
    except Exception as e:
        logging.error(f"❌ Ошибка при запуске бота: {e}")
        exit(1)

if __name__ == '__main__':
    main()
    
    application.run_polling()

if __name__ == '__main__':
    main()
