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
SUPPORT_USERNAME = "@moneytreerefbot"    # ЗАМЕНИТЕ
ADMIN_ID = 955084910                  # ЗАМЕНИТЕ НА ВАШ USER_ID

# Получаем URL базы данных из переменных окружения Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logging.error("❌ DATABASE_URL не найден в переменных окружения!")
    logging.error("Пожалуйста, создайте базу данных PostgreSQL в Railway")
    DATABASE_URL = None

if not TOKEN:
    logging.error("❌ BOT_TOKEN не найден!")
    exit(1)

# ===== БАЗА ДАННЫХ PostgreSQL =====

def get_connection():
    """Создание подключения к PostgreSQL"""
    if not DATABASE_URL:
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        logging.error(f"❌ Ошибка подключения к базе данных: {e}")
        return None

def init_db():
    """Инициализация базы данных"""
    conn = get_connection()
    if not conn:
        logging.warning("⚠️ База данных не доступна, работаем без нее")
        return
    
    try:
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, status)  -- Защита от дублирования
            )
        ''')
        conn.commit()
        conn.close()
        logging.info("✅ База данных PostgreSQL инициализирована")
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации базы данных: {e}")

def add_application(user_id, username, full_name, screenshot_file_id, contact_info):
    """Добавление новой заявки с защитой от дублирования"""
    conn = get_connection()
    if not conn:
        logging.info(f"📝 Заявка от {username} (без сохранения в БД)")
        return True
    
    try:
        cur = conn.cursor()
        
        # Проверяем, есть ли уже активная заявка от этого пользователя
        cur.execute('SELECT id FROM applications WHERE user_id = %s AND status = %s', (user_id, 'pending'))
        existing_app = cur.fetchone()
        
        if existing_app:
            logging.info(f"⚠️ У пользователя {username} уже есть активная заявка #{existing_app[0]}")
            conn.close()
            return False
        
        # Добавляем новую заявку
        cur.execute('''
            INSERT INTO applications (user_id, username, full_name, screenshot_file_id, contact_info)
            VALUES (%s, %s, %s, %s, %s)
        ''', (user_id, username, full_name, screenshot_file_id, contact_info))
        conn.commit()
        conn.close()
        logging.info(f"✅ Заявка добавлена для пользователя {username}")
        return True
    except psycopg2.IntegrityError:
        # Обрабатываем нарушение уникальности
        conn.rollback()
        conn.close()
        logging.warning(f"⚠️ Попытка создания дублирующей заявки от {username}")
        return False
    except Exception as e:
        logging.error(f"❌ Ошибка добавления заявки: {e}")
        conn.close()
        return False

def get_pending_applications():
    """Получение всех ожидающих заявок"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM applications WHERE status = %s ORDER BY created_at DESC', ('pending',))
        applications = cur.fetchall()
        conn.close()
        return applications
    except Exception as e:
        logging.error(f"❌ Ошибка получения заявок: {e}")
        return []

def get_all_applications():
    """Получение всех заявок"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM applications ORDER BY created_at DESC')
        applications = cur.fetchall()
        conn.close()
        return applications
    except Exception as e:
        logging.error(f"❌ Ошибка получения всех заявок: {e}")
        return []

def update_application_status(app_id, status):
    """Обновление статуса заявки"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('UPDATE applications SET status = %s WHERE id = %s', (status, app_id))
        conn.commit()
        conn.close()
        logging.info(f"✅ Статус заявки #{app_id} изменен на {status}")
        return True
    except Exception as e:
        logging.error(f"❌ Ошибка обновления статуса: {e}")
        return False

def get_application_by_user_id(user_id):
    """Получение заявки по user_id"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM applications WHERE user_id = %s AND status = %s', (user_id, 'pending'))
        application = cur.fetchone()
        conn.close()
        return application
    except Exception as e:
        logging.error(f"❌ Ошибка поиска заявки: {e}")
        return None

def get_application_by_id(app_id):
    """Получение заявки по ID"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM applications WHERE id = %s', (app_id,))
        application = cur.fetchone()
        conn.close()
        return application
    except Exception as e:
        logging.error(f"❌ Ошибка поиска заявки по ID: {e}")
        return None

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
🔒 *Политика конфиденциальности:*
• Мы НЕ передаем ваши личные данные третьим лицам
• Мы НЕ используем вашу информацию в корыстных целях
• Ваш username, фамилия имя и реквизиты для выплаты используются *исключительно* для учета выплат
• Все данные удаляются после завершения наших обязательств

*✅ Условия сотрудничества*

*Нажимая «Я согласен», вы подтверждаете, что:*

1. *Действуете добровольно* — мы ни к чему не принуждаем
2. *Ознакомились с условиями акции банка* на официальном сайте (https://acdn.t-static.ru/static/documents/promo-baf-common.pdf)
3. *Понимаете что:* 
   - Вы получаете 1000₽ (500₽ от банка + 500₽ от меня)
   - Я получаю 1000₽ от банка за ваше приглашение
4. *Осознаете,* что это частное предложение, а не оферта банка
5. *Соглашаетесь* на обработку username и ваших реквезитов для учета выплат
6. *Знаете,* что выплата от меня происходит только после успешного выполнения всех условий акции в течении 7 дней.
7. *Гарантируем конфиденциальность:* 
   - Ваши данные (username, реквизиты, ФИ) не передаются третьим лицам
   - Информация не используется в корыстных или мошеннических целях
   - Данные хранятся только для учета выплат и удаляются после выполнения обязательств

💡 *Это взаимовыгодное сотрудничество в рамках акции банка, где каждый получает свою выгоду.* 
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

*Инструкция:*
1. *Оформите карту* по ссылке выше
2. *Совершите покупку* от 500₽ (НЕ: ЖКХ, связь, переводы)
3. *Пришлите скриншот* подтверждения покупки в этот чат
4. *Получите 500₽* от меня в течение 7 дней (обычно это занимает до 24 часов) после проверки📸 
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
*Для получения 500₽ пришлите сюда:*
1. *Скриншот* из приложения банка, подтверждающий покупку
2. *Инициалы* (фамилия, имя) и *Ваши реквизиты* для перевода (номер карты/телефона)

🕐 *Выплата производится в течение 7 дней* после проверки.

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

# ===== ОБРАБОТЧИК СКРИНШОТОВ И ДАННЫХ =====

async def handle_screenshot(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    message = update.message
    
    # Обрабатываем скриншот (фото)
    if message.photo:
        screenshot_file_id = message.photo[-1].file_id
        
        # Проверяем, нет ли уже активной заявки
        existing_app = get_application_by_user_id(user.id)
        if existing_app:
            await message.reply_text("❌ У вас уже есть активная заявка. Дождитесь ее проверки.")
            return
        
        # Сохраняем в базе данных
        success = add_application(user.id, user.username, user.full_name, screenshot_file_id, None)
        
        if success:
            await message.reply_text("✅ Скриншот получен! Теперь отправьте ваши реквизиты для перевода (номер карты или телефона).")
        else:
            await message.reply_text("❌ Не удалось сохранить вашу заявку. Попробуйте позже или обратитесь в поддержку.")
    
    # Обрабатываем текст (реквизиты)
    elif message.text and not message.text.startswith('/'):
        contact_info = message.text
        
        # Ищем активную заявку пользователя
        existing_app = get_application_by_user_id(user.id)
        
        if not existing_app:
            await message.reply_text("❌ Сначала отправьте скриншот подтверждения покупки.")
            return
        
        # Обновляем заявку с реквизитами
        conn = get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute('UPDATE applications SET contact_info = %s WHERE id = %s', 
                           (contact_info, existing_app[0]))
                conn.commit()
                conn.close()
            except Exception as e:
                logging.error(f"❌ Ошибка обновления реквизитов: {e}")
                await message.reply_text("❌ Ошибка при сохранении реквизитов. Попробуйте еще раз.")
                return
        
        # Уведомляем администратора
        admin_text = f"""
🚨 *НОВАЯ ЗАЯВКА #{existing_app[0]}*

👤 *Пользователь:* {user.full_name} (@{user.username})
🆔 *ID:* {user.id}
📞 *Реквизиты:* {contact_info}
📅 *Время:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*Для ответа пользователю:* https://t.me/{user.username}
        """
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📸 Посмотреть скриншот", callback_data=f'view_screenshot_{existing_app[0]}'),
                    InlineKeyboardButton("✅ Одобрить", callback_data=f'approve_{existing_app[0]}')
                ]])
            )
                
        except Exception as e:
            logging.error(f"❌ Ошибка отправки уведомления админу: {e}")
        
        await message.reply_text("✅ Ваши данные получены! Проверка займет до 24 часов. Спасибо!")

# ===== КОМАНДЫ ДЛЯ АДМИНИСТРАТОРА =====

async def view_applications(update: Update, context: CallbackContext) -> None:
    """Просмотр всех заявок с inline кнопками"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    applications = get_pending_applications()
    
    if not applications:
        await update.message.reply_text("📭 Нет заявок для проверки.")
        return
    
    for app in applications:
        app_id, user_id, username, full_name, screenshot_file_id, contact_info, status, created_at = app
        
        text = f"""
📋 *Заявка #{app_id}*
👤 *Пользователь:* {full_name} (@{username})
🆔 *User ID:* {user_id}
📞 *Реквизиты:* {contact_info if contact_info else 'Не указаны'}
📊 *Статус:* {status}
📅 *Дата:* {created_at.strftime('%Y-%m-%d %H:%M')}
        """
        
        keyboard = []
        
        if screenshot_file_id:
            keyboard.append([InlineKeyboardButton("📸 Просмотреть скриншот", callback_data=f'view_screenshot_{app_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton("✅ Одобрить", callback_data=f'approve_{app_id}'),
             InlineKeyboardButton("❌ Отклонить", callback_data=f'reject_{app_id}')]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def view_screenshot(update: Update, context: CallbackContext) -> None:
    """Просмотр скриншота конкретной заявки"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID заявки: /screenshot <id>")
        return
    
    app_id = context.args[0]
    
    app = get_application_by_id(app_id)
    if not app:
        await update.message.reply_text("❌ Заявка не найдена.")
        return
    
    file_id, username, full_name = app[4], app[2], app[3]
    
    if not file_id:
        await update.message.reply_text("❌ В этой заявке нет скриншота.")
        return
    
    # Отправляем скриншот
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=f"📸 Скриншот заявки #{app_id}\n👤 {full_name} (@{username})"
    )

async def view_all_with_screenshots(update: Update, context: CallbackContext) -> None:
    """Просмотр всех заявок со скриншотами"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    applications = get_all_applications()
    
    if not applications:
        await update.message.reply_text("📭 Нет заявок.")
        return
    
    for app in applications:
        app_id, user_id, username, full_name, screenshot_file_id, contact_info, status, created_at = app
        
        if not screenshot_file_id:
            continue
            
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

async def approve_application(update: Update, context: CallbackContext) -> None:
    """Одобрение заявки"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID заявки: /approve <id>")
        return
    
    app_id = context.args[0]
    success = update_application_status(app_id, 'approved')
    
    if not success:
        await update.message.reply_text("❌ Ошибка при обновлении статуса заявки.")
        return
    
    # Уведомляем пользователя
    app = get_application_by_id(app_id)
    if app:
        user_id = app[1]
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 Ваша заявка одобрена! Деньги будут переведены в течение 24 часов."
            )
        except Exception as e:
            logging.error(f"❌ Ошибка уведомления пользователя: {e}")
    
    await update.message.reply_text(f"✅ Заявка #{app_id} одобрена!")

async def reject_application(update: Update, context: CallbackContext) -> None:
    """Отклонение заявки"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID заявки: /reject <id>")
        return
    
    app_id = context.args[0]
    success = update_application_status(app_id, 'rejected')
    
    if not success:
        await update.message.reply_text("❌ Ошибка при обновлении статуса заявки.")
        return
    
    await update.message.reply_text(f"❌ Заявка #{app_id} отклонена!")

# ===== ОБРАБОТЧИК INLINE КНОПОК =====

async def button_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик inline кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('view_screenshot_'):
        app_id = data.split('_')[2]
        
        app = get_application_by_id(app_id)
        if not app or not app[4]:
            await query.edit_message_text("❌ Скриншот не найден.")
            return
        
        file_id, username, full_name = app[4], app[2], app[3]
        
        # Отправляем скриншот отдельным сообщением
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=f"📸 Скриншот заявки #{app_id}\n👤 {full_name} (@{username})"
        )
    
    elif data.startswith('approve_'):
        app_id = data.split('_')[1]
        success = update_application_status(app_id, 'approved')
        
        if success:
            # Уведомляем пользователя
            app = get_application_by_id(app_id)
            if app:
                user_id = app[1]
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="🎉 Ваша заявка одобрена! Деньги будут переведены в течение 7 дней."
                    )
                except Exception as e:
                    logging.error(f"❌ Ошибка уведомления пользователя: {e}")
            
            await query.edit_message_text(f"✅ Заявка #{app_id} одобрена!")
        else:
            await query.edit_message_text("❌ Ошибка при одобрении заявки.")
    
    elif data.startswith('reject_'):
        app_id = data.split('_')[1]
        success = update_application_status(app_id, 'rejected')
        
        if success:
            await query.edit_message_text(f"❌ Заявка #{app_id} отклонена!")
        else:
            await query.edit_message_text("❌ Ошибка при отклонении заявки.")

# ===== ОСНОВНАЯ ФУНКЦИЯ =====

def main() -> None:
    try:
        # Инициализируем базу данных (если доступна)
        init_db()
        
        logging.info("🚀 Запуск бота...")
        application = Application.builder().token(TOKEN).build()
        
        # Обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("view_applications", view_applications))
        application.add_handler(CommandHandler("screenshot", view_screenshot))
        application.add_handler(CommandHandler("all_screenshots", view_all_with_screenshots))
        application.add_handler(CommandHandler("approve", approve_application))
        application.add_handler(CommandHandler("reject", reject_application))
        
        # Обработчики callback-кнопок
        application.add_handler(CallbackQueryHandler(show_terms, pattern='show_terms'))
        application.add_handler(CallbackQueryHandler(get_link, pattern='get_link'))
        application.add_handler(CallbackQueryHandler(instruction, pattern='instruction'))
        application.add_handler(CallbackQueryHandler(back_to_start, pattern='back_to_start'))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Обработчик медиа-сообщений (скриншоты и текст)
        application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_screenshot))
        
        logging.info("✅ Бот успешно запущен и ожидает сообщений")
        application.run_polling()
        
    except Exception as e:
        logging.error(f"❌ Ошибка при запуске бота: {e}")
        exit(1)

if __name__ == '__main__':
    main()
