"""
Хэндлеры для администратора: статистика и рассылка.
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import all_users
from jobs import safe_send

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return

    users   = all_users()
    total   = len(users)
    notify  = sum(1 for u in users if u["notify"])
    evening = sum(1 for u in users if u["evening"])

    groups: dict = {}
    for u in users:
        g = u["group_name"] or u["group_id"] or "—"
        groups[g] = groups.get(g, 0) + 1

    top     = sorted(groups.items(), key=lambda x: -x[1])[:5]
    top_str = "\n".join(f"  {g}: {c} чел." for g, c in top)

    await update.message.reply_text(
        f"👨‍💼 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{total}</b>\n"
        f"🔔 Уведомления 30 мин: <b>{notify}</b>\n"
        f"🌙 Вечерние: <b>{evening}</b>\n\n"
        f"📊 Топ-5 групп:\n{top_str}\n\n"
        f"/broadcast — рассылка\n"
        f"/stats — обновить статистику",
        parse_mode="HTML",
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_admin(update, context)


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return

    if not context.args:
        await update.message.reply_text(
            "📢 Использование:\n<code>/broadcast Текст сообщения</code>\n\nПоддерживается HTML.",
            parse_mode="HTML",
        )
        return

    text  = " ".join(context.args)
    users = all_users()
    await update.message.reply_text(f"📢 Начинаю рассылку {len(users)} пользователям...")

    sent = failed = 0
    for u in users:
        ok = await safe_send(context.bot, u["user_id"], text, parse_mode="HTML")
        sent    += ok
        failed  += not ok
        await asyncio.sleep(0.05)  # ~20 сообщений/сек, ниже лимита Telegram

    await update.message.reply_text(
        f"✅ Рассылка завершена!\n📨 Отправлено: {sent}\n❌ Не доставлено: {failed}"
    )