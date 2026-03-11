"""
Хэндлеры настроек пользователя: язык, уведомления, главное меню.
"""

from telegram import Update
from telegram.ext import ContextTypes

from database import get_attr, get_group_id, get_group_label, set_user, t
from keyboards import main_kb, lang_kb
from texts import TEXTS

LANG_MAP = {"🇷🇺 Русский": "ru", "🇬🇧 English": "en", "🇨🇳 中文": "zh"}


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_user, get_conn
    uid = update.effective_user.id
    if get_user(uid) is None:
        set_user(uid)
        await update.message.reply_text(TEXTS["ru"]["choose_lang"], reply_markup=lang_kb())
        return
    await send_main_menu(update, uid)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(t(uid, "help_text"), parse_mode="HTML")


async def cmd_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cur = get_attr(uid, "notify", 0)
    set_user(uid, notify=0 if cur else 1)
    await update.message.reply_text(
        t(uid, "notify_off" if cur else "notify_on"), parse_mode="HTML"
    )


async def cmd_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cur = get_attr(uid, "evening", 0)
    set_user(uid, evening=0 if cur else 1)
    await update.message.reply_text(
        t(uid, "evening_off" if cur else "evening_on"), parse_mode="HTML"
    )


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TEXTS["ru"]["choose_lang"], reply_markup=lang_kb())


async def send_main_menu(update: Update, user_id: int):
    sub_name = get_attr(user_id, "sub_group_name")
    sub_str  = t(user_id, "subgroup_label").format(sub_name) if sub_name and sub_name not in ("0", "все") else ""
    await update.message.reply_text(
        t(user_id, "start").format(name=get_group_label(user_id), subgroup=sub_str),
        parse_mode="HTML",
        reply_markup=main_kb(user_id),
    )


async def handle_lang_choice(update: Update, uid: int, text: str) -> bool:
    """Обрабатывает выбор языка. Возвращает True если текст был кнопкой языка."""
    if text not in LANG_MAP:
        return False
    set_user(uid, lang=LANG_MAP[text])
    if not get_group_id(uid):
        from group import show_group_picker
        await update.message.reply_text(t(uid, "ask_group"))
        await show_group_picker(update, uid)
    else:
        await send_main_menu(update, uid)
    return True