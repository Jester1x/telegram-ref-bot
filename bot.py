import os
import logging
import psycopg2
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# Настройки
TOKEN = os.environ.get("BOT_TOKEN")
REF_LINK = "https://www.tbank.ru/baf/7Yzkluz5kaS"  # ЗАМЕНИТЕ
SUPPORT_USERNAME = "@otututu"    # ЗАМЕНИТЕ
ADMIN_ID = 955084910                  # ЗАМЕНИТЕ НА ВАШ USER_ID

# Получаем URL базы данных из переменных окружения Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

# ===== БАЗА ДАННЫХ PostgreSQL =====

def get_connection():
    """Создание подключения к PostgreSQL"""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Инициализация базы данных"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
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
    logging.info("✅ База данных PostgreSQL инициализирована")

def add_application(user_id, username, full_name, screenshot_file_id, contact_info):
    """Добавление новой заявки"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO applications (user_id, username, full_name, screenshot_file_id, contact_info)
        VALUES (%s, %s, %s, %s, %s)
    ''', (user_id, username, full_name, screenshot_file_id, contact_info))
    conn.commit()
    conn.close()
    logging.info(f"✅ Заявка добавлена для пользователя {username}")

def get_pending_applications():
    """Получение всех ожидающих заявок"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM applications WHERE status = %s ORDER BY created_at DESC', ('pending',))
    applications = cur.fetchall()
    conn.close()
    return applications

def get_all_applications():
    """Получение всех заявок"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM applications ORDER BY created_at DESC')
    applications = cur.fetchall()
    conn.close()
    return applications

def update_application_status(app_id, status):
    """Обновление статуса заявки"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE applications SET status = %s WHERE id = %s', (status, app_id))
    conn.commit()
    conn.close()
    logging.info(f"✅ Статус заявки #{app_id} изменен на {status}")

def get_application_by_user_id(user_id):
    """Получение заявки по user_id"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM applications WHERE user_id = %s AND status = %s', (user_id, 'pending'))
    application = cur.fetchone()
    conn.close()
    return application

# ===== ОСНОВНЫЕ ФУНКЦИИ БОТА =====

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

# Обработчик скриншотов и контактной информации
async def handle_screenshot(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    message = update.message
    
    # Обрабатываем скриншот (фото)
    if message.photo:
        # Сохраняем информацию о скриншоте
        screenshot_file_id = message.photo[-1].file_id
        
        # Проверяем, есть ли уже заявка от этого пользователя
        existing_app = get_application_by_user_id(user.id)
        
        if existing_app:
            # Обновляем скриншот в существующей заявке
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('UPDATE applications SET screenshot_file_id = %s WHERE id = %s', 
                       (screenshot_file_id, existing_app[0]))
            conn.commit()
            conn.close()
        else:
            # Создаем новую заявку со скриншотом
            add_application(user.id, user.username, user.full_name, screenshot_file_id, None)
        
        await message.reply_text("✅ Скриншот получен! Теперь отправьте ваши реквизиты для перевода (номер карты или телефона).")
    
    # Обрабатываем текст (реквизиты)
    elif message.text and not message.text.startswith('/'):
        contact_info = message.text
        
        # Ищем заявку пользователя
        existing_app = get_application_by_user_id(user.id)
        
        if existing_app and existing_app[4]:  # Если есть заявка и скриншот
            # Обновляем реквизиты
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('UPDATE applications SET contact_info = %s WHERE id = %s', 
                       (contact_info, existing_app[0]))
            conn.commit()
            conn.close()
            
            # Уведомляем администратора
            admin_text = f"""
🚨 *НОВАЯ ЗАЯВКА*

👤 *Пользователь:* {user.full_name} (@{user.username})
🆔 *ID:* {user.id}
📞 *Реквизиты:* {contact_info}
📅 *Время:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*Для проверки заявок используйте команду:* /view_applications
            """
            
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_text,
                    parse_mode='Markdown'
                )
                # Пересылаем скриншот администратору
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=existing_app[4],
                    caption=f"Скриншот от @{user.username}"
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
    
    applications = get_pending_applications()
    
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT user_id, contact_info FROM applications WHERE id = %s', (app_id,))
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
    # Команда для просмотра скриншота конкретной заявки
async def view_screenshot(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID заявки: /screenshot <id>")
        return
    
    app_id = context.args[0]
    
    conn = get_connection()
    if not conn:
        await update.message.reply_text("❌ База данных не доступна.")
        return
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT screenshot_file_id, username, full_name FROM applications WHERE id = %s', (app_id,))
        result = cur.fetchone()
        conn.close()
        
        if not result:
            await update.message.reply_text("❌ Заявка не найдена.")
            return
        
        file_id, username, full_name = result
        
        if not file_id:
            await update.message.reply_text("❌ В этой заявке нет скриншота.")
            return
        
        # Отправляем скриншот
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=f"📸 Скриншот заявки #{app_id}\n👤 {full_name} (@{username})"
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка получения скриншота: {e}")
        await update.message.reply_text("❌ Ошибка при получении скриншота.")

# Команда для просмотра всех заявок со скриншотами
async def view_all_with_screenshots(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    conn = get_connection()
    if not conn:
        await update.message.reply_text("❌ База данных не доступна.")
        return
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, user_id, username, full_name, screenshot_file_id, contact_info, status, created_at 
            FROM applications 
            WHERE screenshot_file_id IS NOT NULL 
            ORDER BY created_at DESC
        ''')
        applications = cur.fetchall()
        conn.close()
        
        if not applications:
            await update.message.reply_text("📭 Нет заявок со скриншотами.")
            return
        
        for app in applications:
            app_id, user_id, username, full_name, screenshot_file_id, contact_info, status, created_at = app
            
            # Отправляем информацию о заявке
            info_text = f"""
📋 *Заявка #{app_id}*
👤 *Пользователь:* {full_name} (@{username})
🆔 *User ID:* {user_id}
📞 *Реквизиты:* {contact_info if contact_info else 'Не указаны'}
📊 *Статус:* {status}
📅 *Дата:* {created_at.strftime('%Y-%m-%d %H:%M')}
            """
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=info_text,
                parse_mode='Markdown'
            )
            
            # Отправляем скриншот
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=screenshot_file_id,
                caption=f"Скриншот заявки #{app_id}"
            )
            
            # Небольшая пауза между сообщениями
            import time
            time.sleep(1)
            
    except Exception as e:
        logging.error(f"❌ Ошибка получения заявок: {e}")
        await update.message.reply_text("❌ Ошибка при получении заявок.")
