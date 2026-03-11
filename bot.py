"""
Точка входа. Регистрирует все хэндлеры и запускает бота.

Установка зависимостей:
    pip install "python-telegram-bot[job-queue]==20.7" requests python-dotenv

Запуск:
    python bot.py
"""

import logging
from datetime import time

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

from config import BOT_TOKEN, TZ, EVENING_HOUR, ADMIN_IDS
from database import get_conn, get_group_id, get_attr, set_user, t
from api import fetch_schedule
from keyboards import main_kb, lang_kb
from texts import TEXTS

# Хэндлеры
from handlers.schedule  import cmd_today, cmd_tomorrow, cmd_week, cmd_nextweek
from handlers.group     import cmd_setgroup, callback_group_navigation, show_group_picker
from handlers.settings  import cmd_start, cmd_help, cmd_notify, cmd_evening, cmd_lang, send_main_menu, handle_lang_choice
from handlers.admin     import cmd_admin, cmd_stats, cmd_broadcast

# Фоновые задачи
from jobs import job_notify_30min, job_evening

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Обработчик текстовых кнопок ─────────────────────────────────────────────

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Роутер текстовых сообщений.
    Обрабатывает кнопки Reply-клавиатуры и ввод группы вручную.
    """
    uid  = update.effective_user.id
    text = update.message.text

    # Выбор языка
    if await handle_lang_choice(update, uid, text):
        return

    # Пользователь ещё не выбрал группу
    if not get_group_id(uid):
        if text.isdigit():
            await update.message.reply_text(t(uid, "loading"))
            schedule = fetch_schedule(text)
            if schedule:
                set_user(uid, group_id=text, group_name=text)
                await update.message.reply_text(t(uid, "group_ok").format(text), parse_mode="HTML")
                await send_main_menu(update, uid)
            else:
                await update.message.reply_text(t(uid, "group_err"))
        else:
            await show_group_picker(update, uid)
        return

    # Карта кнопок → команды
    btn_map = {
        "btn_today":   cmd_today,
        "btn_tomorrow":cmd_tomorrow,
        "btn_week":    cmd_week,
        "btn_nextweek":cmd_nextweek,
        "btn_notify":  cmd_notify,
        "btn_evening": cmd_evening,
        "btn_lang":    cmd_lang,
    }
    for key, handler in btn_map.items():
        if text in [TEXTS[lang].get(key, "") for lang in TEXTS]:
            await handler(update, context)
            return

    # Кнопка смены группы
    if text in [TEXTS[lang].get("btn_group", "") for lang in TEXTS]:
        await show_group_picker(update, uid)


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    # Инициализация БД
    get_conn()

    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    commands = [
        ("start",     cmd_start),
        ("help",      cmd_help),
        ("today",     cmd_today),
        ("tomorrow",  cmd_tomorrow),
        ("week",      cmd_week),
        ("nextweek",  cmd_nextweek),
        ("notify",    cmd_notify),
        ("evening",   cmd_evening),
        ("lang",      cmd_lang),
        ("setgroup",  cmd_setgroup),
        ("admin",     cmd_admin),
        ("stats",     cmd_stats),
        ("broadcast", cmd_broadcast),
    ]
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    # Inline-навигация групп
    app.add_handler(CallbackQueryHandler(callback_group_navigation))

    # Текстовые кнопки
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))

    # Фоновые задачи
    app.job_queue.run_repeating(job_notify_30min, interval=60, first=15)
    app.job_queue.run_daily(job_evening, time=time(EVENING_HOUR, 0, tzinfo=TZ))

    logger.info("🤖 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()