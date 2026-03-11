"""
Все клавиатуры бота: Reply и InlineKeyboard.
"""

from telegram import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from database import t
from texts import TEXTS
from config import FAC_PAGE_SIZE, GRP_PAGE_SIZE


# ─── Reply-клавиатуры ─────────────────────────────────────────────────────────

def main_kb(user_id: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton(t(user_id, "btn_today")),    KeyboardButton(t(user_id, "btn_tomorrow"))],
        [KeyboardButton(t(user_id, "btn_week")),     KeyboardButton(t(user_id, "btn_nextweek"))],
        [KeyboardButton(t(user_id, "btn_notify")),   KeyboardButton(t(user_id, "btn_evening"))],
        [KeyboardButton(t(user_id, "btn_group")),    KeyboardButton(t(user_id, "btn_lang"))],
    ], resize_keyboard=True)


def lang_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["🇷🇺 Русский", "🇬🇧 English", "🇨🇳 中文"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ─── Inline-клавиатуры навигации групп ───────────────────────────────────────
#
# Callback-схема (уровни дерева):
#   fp:{page}                           — пагинация факультетов
#   f:{fi}                              — выбор факультета
#   fo:{fi}:{fmi}                       — выбор формы обучения
#   fl:{fi}:{fmi}:{li}                  — выбор ступени
#   fc:{fi}:{fmi}:{li}:{ci}             — выбор курса
#   gp:{fi}:{fmi}:{li}:{ci}:{page}      — пагинация групп
#   g:{group_id}:{short_name}           — выбор группы
#   sg:{group_id}:{sg_id}:{sg_name}     — выбор подгруппы
#

def fac_kb(tree: dict, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура выбора факультета с пагинацией."""
    facs  = list(tree.keys())
    total = len(facs)
    start = page * FAC_PAGE_SIZE
    end   = min(start + FAC_PAGE_SIZE, total)

    btns = []
    for i in range(start, end):
        label = (facs[i]
                 .replace("институт ", "")
                 .replace("факультет ", "")
                 .replace("филиал ", "")
                 .strip().capitalize()[:42])
        btns.append([InlineKeyboardButton(label, callback_data=f"f:{i}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"fp:{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"fp:{page + 1}"))
    if nav:
        btns.append(nav)
    return InlineKeyboardMarkup(btns)


def simple_list_kb(items: list[str], cb_prefix: str, back_cb: str | None = None) -> InlineKeyboardMarkup:
    """Простой список кнопок с опциональной кнопкой Назад."""
    btns = [
        [InlineKeyboardButton(item[:42], callback_data=f"{cb_prefix}:{i}")]
        for i, item in enumerate(items)
    ]
    if back_cb:
        btns.append([InlineKeyboardButton("🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(btns)


def groups_kb(groups: list[tuple], fi: int, fmi: int, li: int, ci: int,
              page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура выбора группы с пагинацией."""
    total = len(groups)
    start = page * GRP_PAGE_SIZE
    end   = min(start + GRP_PAGE_SIZE, total)

    btns = []
    for i in range(start, end):
        gname, meta = groups[i]
        gid   = meta["id"]
        short = gname[:18].replace(":", "")
        btns.append([InlineKeyboardButton(gname[:42], callback_data=f"g:{gid}:{short}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"gp:{fi}:{fmi}:{li}:{ci}:{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"gp:{fi}:{fmi}:{li}:{ci}:{page + 1}"))
    if nav:
        btns.append(nav)

    btns.append([InlineKeyboardButton("🔙 Назад", callback_data=f"fc:{fi}:{fmi}:{li}")])
    return InlineKeyboardMarkup(btns)


def subgroup_kb(group_id: int | str, sub_groups: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора подгруппы."""
    btns = []
    for i, sg in enumerate(sub_groups):
        label = sg.get("name") or f"Подгруппа {i + 1}"
        sg_name = (sg.get("name") or str(i + 1))[:15]
        btns.append([InlineKeyboardButton(label, callback_data=f"sg:{group_id}:{sg['id']}:{sg_name}")])
    btns.append([InlineKeyboardButton("Без подгруппы", callback_data=f"sg:{group_id}:0:все")])
    return InlineKeyboardMarkup(btns)


def site_btn(group_id: str) -> InlineKeyboardMarkup:
    """Кнопка-ссылка на сайт."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🌐 Открыть на сайте",
            url=f"https://guide.herzen.spb.ru/schedule/{group_id}/by-dates"
        )
    ]])