"""
Хэндлеры выбора группы: показ дерева факультетов, навигация, подгруппы.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database import get_group_id, get_group_label, get_attr, set_user, t
from api import fetch_groups_tree, fetch_schedule, find_sub_groups, invalidate_schedule
from keyboards import (
    fac_kb, simple_list_kb, groups_kb,
    subgroup_kb, site_btn, main_kb,
)
from texts import TEXTS

logger = logging.getLogger(__name__)


# ─── Показ выборщика группы ──────────────────────────────────────────────────

async def show_group_picker(update: Update, user_id: int):
    """Запускает процесс выбора группы — показывает список факультетов."""
    msg = update.message
    await msg.reply_text(t(user_id, "loading_fac"))
    tree = fetch_groups_tree()
    if not tree:
        await msg.reply_text(t(user_id, "setgroup_hint"), parse_mode="HTML")
        return
    await msg.reply_text(t(user_id, "choose_fac"), reply_markup=fac_kb(tree))


async def cmd_setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /setgroup [id] — задать группу вручную или открыть выборщик."""
    user_id = update.effective_user.id
    if not context.args:
        await show_group_picker(update, user_id)
        return

    gid = context.args[0].strip()
    if not gid.isdigit():
        await update.message.reply_text(t(user_id, "group_invalid"))
        return

    await update.message.reply_text(t(user_id, "loading"))
    invalidate_schedule(gid)
    schedule = fetch_schedule(gid)

    if not schedule:
        await update.message.reply_text(t(user_id, "group_err"))
        return

    set_user(user_id, group_id=gid, group_name=gid, sub_group_id=None, sub_group_name=None)
    await update.message.reply_text(
        t(user_id, "setgroup_ok").format(gid, len(schedule)), parse_mode="HTML"
    )
    await _send_main_menu(update, user_id)


# ─── Callback-навигация ──────────────────────────────────────────────────────

async def callback_group_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик всей inline-навигации по дереву групп."""
    query = update.callback_query
    uid   = query.from_user.id
    data  = query.data
    await query.answer()

    tree = fetch_groups_tree()
    if not tree:
        await query.edit_message_text(t(uid, "setgroup_hint"), parse_mode="HTML")
        return

    fac_list = list(tree.keys())

    # ── Пагинация факультетов
    if data.startswith("fp:"):
        page = int(data.split(":")[1])
        await query.edit_message_text(
            t(uid, "choose_fac"), reply_markup=fac_kb(tree, page)
        )

    # ── Выбор факультета → форма обучения (или ступень если одна форма)
    elif data.startswith("f:") and not any(data.startswith(p) for p in ("fo:", "fp:", "fc:")):
        fi  = int(data.split(":")[1])
        fac = fac_list[fi]
        forms = list(tree[fac].keys())
        lbl   = _fac_label(fac)

        if len(forms) == 1:
            fmi    = 0
            levels = list(tree[fac][forms[0]].keys())
            await query.edit_message_text(
                f"🏛 <b>{lbl}</b>\n\n{t(uid, 'choose_level')}", parse_mode="HTML",
                reply_markup=simple_list_kb(levels, f"fl:{fi}:{fmi}", "fp:0"),
            )
        else:
            await query.edit_message_text(
                f"🏛 <b>{lbl}</b>\n\n{t(uid, 'choose_form')}", parse_mode="HTML",
                reply_markup=simple_list_kb(forms, f"fo:{fi}", "fp:0"),
            )

    # ── Выбор формы → ступень (или курс если одна ступень)
    elif data.startswith("fo:"):
        _, fi_s, fmi_s = data.split(":")
        fi, fmi = int(fi_s), int(fmi_s)
        fac    = fac_list[fi]
        form   = list(tree[fac].keys())[fmi]
        levels = list(tree[fac][form].keys())
        lbl    = _fac_label(fac)

        if len(levels) == 1:
            li      = 0
            courses = list(tree[fac][form][levels[0]].keys())
            await query.edit_message_text(
                f"🏛 <b>{lbl}</b> · {form}\n\n{t(uid, 'choose_course')}", parse_mode="HTML",
                reply_markup=simple_list_kb(_course_labels(courses), f"fc:{fi}:{fmi}:{li}", f"f:{fi}"),
            )
        else:
            await query.edit_message_text(
                f"🏛 <b>{lbl}</b> · {form}\n\n{t(uid, 'choose_level')}", parse_mode="HTML",
                reply_markup=simple_list_kb(levels, f"fl:{fi}:{fmi}", f"f:{fi}"),
            )

    # ── Выбор ступени → курс
    elif data.startswith("fl:"):
        parts       = data.split(":")
        fi, fmi, li = int(parts[1]), int(parts[2]), int(parts[3])
        fac         = fac_list[fi]
        form        = list(tree[fac].keys())[fmi]
        level       = list(tree[fac][form].keys())[li]
        courses     = list(tree[fac][form][level].keys())
        lbl         = _fac_label(fac)

        await query.edit_message_text(
            f"🏛 <b>{lbl}</b> · {level}\n\n{t(uid, 'choose_course')}", parse_mode="HTML",
            reply_markup=simple_list_kb(_course_labels(courses), f"fc:{fi}:{fmi}:{li}", f"fo:{fi}:{fmi}"),
        )

    # ── Выбор курса → список групп
    elif data.startswith("fc:"):
        parts           = data.split(":")
        fi, fmi, li, ci = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
        fac             = fac_list[fi]
        form            = list(tree[fac].keys())[fmi]
        level           = list(tree[fac][form].keys())[li]
        course          = list(tree[fac][form][level].keys())[ci]
        groups          = list(tree[fac][form][level][course].items())
        lbl             = _fac_label(fac)
        clbl            = f"{course} курс" if course.isdigit() else course

        await query.edit_message_text(
            f"🏛 <b>{lbl}</b> · {clbl}\n\n{t(uid, 'choose_group')}", parse_mode="HTML",
            reply_markup=groups_kb(groups, fi, fmi, li, ci),
        )

    # ── Пагинация групп
    elif data.startswith("gp:"):
        parts               = data.split(":")
        fi, fmi, li, ci, pg = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
        fac                 = fac_list[fi]
        form                = list(tree[fac].keys())[fmi]
        level               = list(tree[fac][form].keys())[li]
        course              = list(tree[fac][form][level].keys())[ci]
        groups              = list(tree[fac][form][level][course].items())

        await query.edit_message_text(
            t(uid, "choose_group"),
            reply_markup=groups_kb(groups, fi, fmi, li, ci, pg),
        )

    # ── Выбор группы
    elif data.startswith("g:") and not data.startswith("gp:"):
        parts    = data.split(":", 2)
        group_id = parts[1]
        gname    = parts[2] if len(parts) > 2 else parts[1]

        await query.edit_message_text(
            f"⏳ Загружаю расписание для <b>{gname}</b>...", parse_mode="HTML"
        )

        sub_groups = find_sub_groups(group_id)
        set_user(uid, group_id=group_id, group_name=gname, sub_group_id=None, sub_group_name=None)

        if sub_groups:
            # Есть подгруппы — предлагаем выбрать
            await query.edit_message_text(
                f"👥 <b>{gname}</b>\n\n{t(uid, 'choose_subgroup')}",
                parse_mode="HTML",
                reply_markup=subgroup_kb(group_id, sub_groups),
            )
        else:
            schedule = fetch_schedule(group_id)
            msg = t(uid, "group_ok").format(gname) if schedule else t(uid, "group_empty").format(gname)
            await query.edit_message_text(msg, parse_mode="HTML")
            await context.bot.send_message(
                uid,
                t(uid, "start").format(name=gname, subgroup=""),
                parse_mode="HTML",
                reply_markup=main_kb(uid),
            )

    # ── Выбор подгруппы
    elif data.startswith("sg:"):
        parts    = data.split(":", 3)
        group_id = parts[1]
        sg_id    = parts[2]
        sg_name  = parts[3] if len(parts) > 3 else sg_id
        gname    = get_attr(uid, "group_name") or group_id

        schedule = fetch_schedule(group_id, sg_id if sg_id != "0" else None)
        set_user(
            uid,
            group_id=group_id, group_name=gname,
            sub_group_id=sg_id if sg_id != "0" else None,
            sub_group_name=sg_name if sg_id != "0" else None,
        )

        sub_str = t(uid, "subgroup_label").format(sg_name) if sg_id != "0" else ""
        msg     = t(uid, "group_ok").format(gname) if schedule else t(uid, "group_empty").format(gname)

        await query.edit_message_text(msg, parse_mode="HTML")
        await context.bot.send_message(
            uid,
            t(uid, "start").format(name=gname, subgroup=sub_str),
            parse_mode="HTML",
            reply_markup=main_kb(uid),
        )


# ─── Вспомогательные ─────────────────────────────────────────────────────────

def _fac_label(fac: str) -> str:
    return (fac.replace("институт ", "")
               .replace("факультет ", "")
               .replace("филиал ", "")
               .strip().capitalize())


def _course_labels(courses: list[str]) -> list[str]:
    return [f"{c} курс" if c.isdigit() else c for c in courses]


async def _send_main_menu(update: Update, user_id: int):
    sub_name = get_attr(user_id, "sub_group_name")
    sub_str  = t(user_id, "subgroup_label").format(sub_name) if sub_name and sub_name not in ("0", "все") else ""
    await update.message.reply_text(
        t(user_id, "start").format(name=get_group_label(user_id), subgroup=sub_str),
        parse_mode="HTML",
        reply_markup=main_kb(user_id),
    )