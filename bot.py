import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# Проверка токена
TOKEN = os.environ.get("BOT_TOKEN")
REF_LINK = "https://www.tbank.ru/baf/7Yzkluz5kaS"
SUPPORT_USERNAME = "@otututu"
ADMIN_ID = 955084910  # ЗАМЕНИТЕ НА ВАШ USER_ID в Telegram

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('applications.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            screenshot_file_id TEXT,
            contact_info TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Функция для добавления заявки
def add_application(user_id, username, full_name, screenshot_file_id, contact_info):
    conn = sqlite3.connect('applications.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO applications (user_id, username, full_name, screenshot_file_id, contact_info)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, full_name, screenshot_file_id, contact_info))
    conn.commit()
    conn.close()

# Функция для получения всех заявок
def get_applications():
    conn = sqlite3.connect('applications.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM applications ORDER BY created_at DESC')
    applications = cur.fetchall()
    conn.close()
    return applications

# Функция для обновления статуса заявки
def update_application_status(app_id, status):
    conn = sqlite3.connect('applications.db')
    cur = conn.cursor()
    cur.execute('UPDATE applications SET status = ? WHERE id = ?', (status, app_id))
    conn.commit()
    conn.close()

# Обработчик скриншотов и контактной информации
async def handle_screenshot(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    message = update.message
    
    # Сохраняем информацию о пользователе
    user_info = {
        'user_id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'screenshot_file_id': None,
        'contact_info': None
    }
    
    # Обрабатываем скриншот (фото)
    if message.photo:
        user_info['screenshot_file_id'] = message.photo[-1].file_id
        await message.reply_text("✅ Скриншот получен! Теперь отправьте ваши реквизиты для перевода (номер карты или телефона).")
    
    # Обрабатываем текст (реквизиты)
    elif message.text and not message.text.startswith('/'):
        # Проверяем, есть ли уже скриншот от этого пользователя
        conn = sqlite3.connect('applications.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM applications WHERE user_id = ? AND status = "pending"', (user.id,))
        existing_app = cur.fetchone()
        conn.close()
        
        if existing_app:
            # Обновляем реквизиты
            user_info['contact_info'] = message.text
            add_application(user.id, user.username, user.full_name, existing_app[4], message.text)
            
            # Уведомляем администратора
            admin_text = f"""
🚨 *НОВАЯ ЗАЯВКА*

👤 *Пользователь:* {user.full_name} (@{user.username})
🆔 *ID:* {user.id}
📞 *Реквизиты:* {message.text}
📅 *Время:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*Для проверки скриншота используйте команду:* /view_applications
            """
            
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_text,
                    parse_mode='Markdown'
                )
                # Пересылаем скриншот администратору
                await context.bot.forward_message(
                    chat_id=ADMIN_ID,
                    from_chat_id=message.chat_id,
                    message_id=existing_app[0]
                )
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления админу: {e}")
            
            await message.reply_text("✅ Ваши данные получены! Проверка займет до 24 часов. Спасибо!")
        else:
            await message.reply_text("❌ Сначала отправьте скриншот подтверждения покупки.")

# Команда для администратора - просмотр заявок
async def view_applications(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    
    # Проверяем, является ли пользователь администратором
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    applications = get_applications()
    
    if not applications:
        await update.message.reply_text("📭 Нет заявок для проверки.")
        return
    
    text = "📋 *Список заявок:*\n\n"
    for app in applications:
        status_emoji = "⏳" if app[6] == 'pending' else "✅" if app[6] == 'approved' else "❌"
        text += f"{status_emoji} *Заявка #{app[0]}*\n"
        text += f"👤 {app[3]} (@{app[2]})\n"
        text += f"📞 {app[5]}\n"
        text += f"📅 {app[7]}\n"
        text += f"🆔 User ID: {app[1]}\n"
        text += f"📊 Статус: {app[6]}\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

# Команда для одобрения заявки
async def approve_application(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID заявки: /approve <id>")
        return
    
    app_id = context.args[0]
    update_application_status(app_id, 'approved')
    
    # Получаем информацию о заявке для уведомления пользователя
    conn = sqlite3.connect('applications.db')
    cur = conn.cursor()
    cur.execute('SELECT user_id, contact_info FROM applications WHERE id = ?', (app_id,))
    app = cur.fetchone()
    conn.close()
    
    if app:
        try:
            await context.bot.send_message(
                chat_id=app[0],
                text="🎉 Ваша заявка одобрена! Деньги будут переведены в течение 24 часов."
            )
        except Exception as e:
            logging.error(f"Ошибка уведомления пользователя: {e}")
    
    await update.message.reply_text(f"✅ Заявка #{app_id} одобрена!")

# ... остальные функции (start, show_terms, get_link, instruction, back_to_start) остаются без изменений ...

def main() -> None:
    try:
        # Инициализируем базу данных
        init_db()
        
        logging.info("🚀 Запуск бота...")
        application = Application.builder().token(TOKEN).build()
        
        # Обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("view_applications", view_applications))
        application.add_handler(CommandHandler("approve", approve_application))
        
        # Обработчики callback-кнопок
        application.add_handler(CallbackQueryHandler(show_terms, pattern='show_terms'))
        application.add_handler(CallbackQueryHandler(get_link, pattern='get_link'))
        application.add_handler(CallbackQueryHandler(instruction, pattern='instruction'))
        application.add_handler(CallbackQueryHandler(back_to_start, pattern='back_to_start'))
        
        # Обработчик медиа-сообщений (скриншоты и текст)
        application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_screenshot))
        
        logging.info("✅ Бот успешно запущен и ожидает сообщений")
        application.run_polling()
        
    except Exception as e:
        logging.error(f"❌ Ошибка при запуске бота: {e}")
        exit(1)

if __name__ == '__main__':
    main()
