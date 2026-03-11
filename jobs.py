"""
Фоновые задачи: уведомления за 30 минут и вечерняя рассылка.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from telegram.error import Forbidden, RetryAfter
from telegram.ext import ContextTypes

from config import TZ
from database import all_users, t
from api import fetch_schedule
from formatter import get_day_lessons, format_lesson
from keyboards import site_btn
from texts import TEXTS

logger = logging.getLogger(__name__)


# ─── Безопасная отправка ─────────────────────────────────────────────────────

async def safe_send(bot, user_id: int, text: str, **kwargs) -> bool:
    """
    Отправляет сообщение пользователю.
    Обрабатывает блокировку бота (Forbidden) и превышение лимита (RetryAfter).
    Возвращает True при успехе.
    """
    try:
        await bot.send_message(chat_id=user_id, text=text, **kwargs)
        return True
    except Forbidden:
        logger.warning(f"Пользователь {user_id} заблокировал бота.")
        from database import set_user
        set_user(user_id, notify=0, evening=0)
        return False
    except RetryAfter as e:
        logger.warning(f"RetryAfter: ждём {e.retry_after} сек.")
        await asyncio.sleep(e.retry_after)
        return await safe_send(bot, user_id, text, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка отправки {user_id}: {e}")
        return False


# ─── Уведомления за 30 минут ─────────────────────────────────────────────────

async def job_notify_30min(context: ContextTypes.DEFAULT_TYPE):
    """Запускается каждую минуту. Отправляет напоминание если до занятия 28–32 минуты."""
    now = datetime.now(TZ)
    for row in all_users():
        if not row["notify"] or not row["group_id"]:
            continue
        try:
            schedule = fetch_schedule(row["group_id"], row["sub_group_id"])
            for lesson in get_day_lessons(schedule, now.date()):
                lesson_dt = datetime.combine(lesson["date"], lesson["time_start"], tzinfo=TZ)
                diff_min  = (lesson_dt - now).total_seconds() / 60
                if 28 <= diff_min <= 32:
                    await safe_send(
                        context.bot,
                        row["user_id"],
                        t(row["user_id"], "notify_soon") + format_lesson(lesson),
                        parse_mode="HTML",
                    )
        except Exception as e:
            logger.error(f"job_notify_30min error for {row['user_id']}: {e}")


# ─── Вечерняя рассылка ───────────────────────────────────────────────────────

async def job_evening(context: ContextTypes.DEFAULT_TYPE):
    """Запускается ровно в 20:00 МСК. Отправляет расписание на завтра."""
    tomorrow = datetime.now(TZ).date() + timedelta(days=1)

    for row in all_users():
        if not row["evening"] or not row["group_id"]:
            continue
        try:
            uid      = row["user_id"]
            lang     = row["lang"] or "ru"
            schedule = fetch_schedule(row["group_id"], row["sub_group_id"])
            lessons  = get_day_lessons(schedule, tomorrow)

            days    = TEXTS[lang]["days"]
            header  = (
                f"🌙 <b>Расписание на завтра:</b>\n"
                f"📅 <b>{days[tomorrow.weekday()]}, {tomorrow.strftime('%d.%m.%Y')}</b>\n\n"
            )
            body = (
                "\n\n".join(format_lesson(l) for l in lessons)
                if lessons else
                TEXTS[lang].get("no_tomorrow", "Занятий нет 🎉")
            )

            await safe_send(
                context.bot, uid, header + body,
                parse_mode="HTML",
                reply_markup=site_btn(row["group_id"]),
            )
            await asyncio.sleep(0.05)  # Защита от flood limit при большой базе

        except Exception as e:
            logger.error(f"job_evening error for {row['user_id']}: {e}")