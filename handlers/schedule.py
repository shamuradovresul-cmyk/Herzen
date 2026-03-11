"""
Хэндлеры расписания: сегодня, завтра, неделя, следующая неделя.
"""

import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from config import TZ
from database import get_group_id, get_attr, t
from api import fetch_schedule
from formatter import (
    get_day_lessons, get_week_lessons,
    format_day, week_to_messages,
)
from keyboards import site_btn

logger = logging.getLogger(__name__)


async def send_day(update: Update, context: ContextTypes.DEFAULT_TYPE, offset_days: int = 0):
    """Отправляет расписание на конкретный день (0 = сегодня, 1 = завтра)."""
    user_id  = update.effective_user.id
    group_id = get_group_id(user_id)

    if not group_id:
        await update.message.reply_text(t(user_id, "setgroup_hint"), parse_mode="HTML")
        return

    await update.message.reply_text(t(user_id, "loading"))

    sub_id   = get_attr(user_id, "sub_group_id")
    target   = datetime.now(TZ).date() + timedelta(days=offset_days)
    schedule = fetch_schedule(group_id, sub_id)
    lessons  = get_day_lessons(schedule, target)

    await update.message.reply_text(
        format_day(target, lessons, user_id),
        parse_mode="HTML",
        reply_markup=site_btn(group_id),
    )


async def send_week(update: Update, context: ContextTypes.DEFAULT_TYPE, offset: int = 0):
    """Отправляет расписание на неделю (0 = текущая, 1 = следующая)."""
    user_id  = update.effective_user.id
    group_id = get_group_id(user_id)

    if not group_id:
        await update.message.reply_text(t(user_id, "setgroup_hint"), parse_mode="HTML")
        return

    await update.message.reply_text(t(user_id, "loading_week"))

    sub_id   = get_attr(user_id, "sub_group_id")
    today    = datetime.now(TZ).date()
    schedule = fetch_schedule(group_id, sub_id)
    week     = get_week_lessons(schedule, today, offset)

    if not week:
        key = "no_week" if offset == 0 else "no_nextweek"
        await update.message.reply_text(t(user_id, key))
        return

    messages = week_to_messages(week, user_id)
    btn      = site_btn(group_id)

    for i, msg_text in enumerate(messages):
        # Кнопку добавляем только к последнему сообщению
        kb = btn if i == len(messages) - 1 else None
        await update.message.reply_text(msg_text, parse_mode="HTML", reply_markup=kb)


# ── Команды ───────────────────────────────────────────────────────────────────

async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_day(update, context, offset_days=0)

async def cmd_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_day(update, context, offset_days=1)

async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_week(update, context, offset=0)

async def cmd_nextweek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_week(update, context, offset=1)