"""
Форматирование расписания в текст для Telegram.
"""

from datetime import date, timedelta
from database import t
from texts import TEXTS

TYPE_EMOJI = {
    "лекц":      "📖",
    "практ":     "✏️",
    "лаб":       "🔬",
    "зачёт":     "📝",
    "зачет":     "📝",
    "экзамен":   "🎓",
    "консульт":  "💬",
    "видеолекц": "🖥",
}


def format_lesson(lesson: dict) -> str:
    """Форматирует одно занятие."""
    lt    = lesson.get("type", "").lower()
    emoji = next((em for kw, em in TYPE_EMOJI.items() if kw in lt), "📌")

    lines = [f"{emoji} <b>{lesson['time_start_str']}–{lesson['time_end_str']}</b>",
             f"    <b>{lesson['subject']}</b>"]

    type_line = ""
    if lt:
        type_line = f"    <i>{lt}</i>"
        if lesson.get("note"):
            type_line += f" · {lesson['note']}"
    elif lesson.get("note"):
        type_line = f"    <i>{lesson['note']}</i>"
    if type_line:
        lines.append(type_line)

    if lesson.get("teacher"):
        lines.append(f"    👤 {lesson['teacher']}")
    if lesson.get("room"):
        lines.append(f"    🏫 {lesson['room']}")

    return "\n".join(lines)


def format_day(target: date, lessons: list[dict], user_id: int = 0) -> str:
    """Форматирует один день расписания."""
    from database import get_lang
    days   = TEXTS.get(get_lang(user_id), TEXTS["ru"])["days"]
    header = f"📅 <b>{days[target.weekday()]}, {target.strftime('%d.%m.%Y')}</b>\n\n"
    body   = "\n\n".join(format_lesson(l) for l in lessons) if lessons else t(user_id, "no_lessons")
    return header + body


def get_day_lessons(schedule: list[dict], target: date) -> list[dict]:
    """Фильтрует занятия по дате."""
    return [l for l in schedule if l["date"] == target]


def get_week_lessons(schedule: list[dict], target: date, offset: int = 0) -> dict[date, list[dict]]:
    """Возвращает занятия за неделю со смещением offset (0 = текущая, 1 = следующая)."""
    monday = target - timedelta(days=target.weekday()) + timedelta(weeks=offset)
    sunday = monday + timedelta(days=6)
    result: dict[date, list[dict]] = {}
    for lesson in schedule:
        if monday <= lesson["date"] <= sunday:
            result.setdefault(lesson["date"], []).append(lesson)
    return result


def week_to_messages(week: dict[date, list[dict]], user_id: int) -> list[str]:
    """
    Собирает дни недели в список сообщений.
    Объединяет дни в одно сообщение пока не превысит лимит Telegram (3800 символов).
    """
    messages = []
    chunk    = ""
    for d, lessons in sorted(week.items()):
        day_text = format_day(d, lessons, user_id)
        if len(chunk) + len(day_text) > 3800:
            if chunk:
                messages.append(chunk.strip())
            chunk = day_text + "\n\n"
        else:
            chunk += day_text + "\n\n"
    if chunk:
        messages.append(chunk.strip())
    return messages