"""
Работа с официальным API РГПУ: https://api.herzen.spb.ru/schedule/v1
Содержит кэширование групп и расписания в памяти.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Any
from zoneinfo import ZoneInfo

import requests

from config import API_BASE, CACHE_TTL_HOURS, GROUPS_TTL_HOURS, TZ

logger = logging.getLogger(__name__)

# ─── Кэш ─────────────────────────────────────────────────────────────────────

_schedule_cache: dict[str, dict] = {}   # "{group}:{sub}:{from}:{to}" → {lessons, time}
_groups_tree:    dict | None = None
_groups_tree_ts: datetime | None = None


# ─── Базовый запрос ──────────────────────────────────────────────────────────

def api_get(endpoint: str, params: dict | None = None) -> Any:
    try:
        r = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        logger.error(f"API timeout: {endpoint}")
    except requests.exceptions.RequestException as e:
        logger.error(f"API error [{endpoint}]: {e}")
    except Exception as e:
        logger.error(f"API unexpected [{endpoint}]: {e}")
    return None


# ─── Дерево групп ─────────────────────────────────────────────────────────────

def fetch_groups_tree() -> dict | None:
    """
    Возвращает дерево групп:
    { факультет → { форма → { ступень → { курс → { название_группы → {id, sub_groups} } } } } }
    """
    global _groups_tree, _groups_tree_ts

    # Проверяем свежесть кэша
    if (_groups_tree is not None and _groups_tree_ts is not None and
            (datetime.now() - _groups_tree_ts).total_seconds() < GROUPS_TTL_HOURS * 3600):
        return _groups_tree

    groups_data     = api_get("groups")
    faculties_data  = api_get("faculties")
    sub_groups_data = api_get("sub_groups")

    if not isinstance(groups_data, list) or not isinstance(faculties_data, list):
        logger.warning("Не удалось загрузить дерево групп, используем старый кэш.")
        return _groups_tree  # Вернём устаревший кэш если API недоступен

    fac_map: dict[int, str] = {}
    for f in faculties_data:
        try:
            fac_map[int(f["id"])] = f.get("name", "")
        except (KeyError, TypeError, ValueError):
            pass

    sg_map: dict[int, dict] = {}
    if isinstance(sub_groups_data, list):
        for sg in sub_groups_data:
            try:
                sg_map[int(sg["id"])] = sg
            except (KeyError, TypeError, ValueError):
                pass

    tree: dict = {}
    for g in groups_data:
        try:
            gid      = int(g["id"])
            fac_id   = int(g.get("faculty_id") or 0)
            fac_name = fac_map.get(fac_id, f"Факультет {fac_id}")
            form     = (g.get("education_form")  or "неизвестно").strip()
            level    = (g.get("education_level") or "неизвестно").strip()
            course   = str(g.get("course") or "")
            gname    = (g.get("name") or f"Группа {gid}").strip()

            # Подгруппы
            sub_groups = []
            for sgid in (g.get("sub_group_ids") or []):
                try:
                    sgid = int(sgid)
                    d    = sg_map.get(sgid, {})
                    sub_groups.append({"id": sgid, "name": d.get("name") or str(len(sub_groups) + 1)})
                except (TypeError, ValueError):
                    pass

            leaf: dict = {"id": gid}
            if sub_groups:
                leaf["sub_groups"] = sub_groups

            (tree
             .setdefault(fac_name, {})
             .setdefault(form, {})
             .setdefault(level, {})
             .setdefault(course, {})[gname]) = leaf

        except (KeyError, TypeError, ValueError) as e:
            logger.debug(f"Пропуск группы: {e}")

    _groups_tree    = tree
    _groups_tree_ts = datetime.now()
    logger.info(f"Дерево групп загружено: {len(groups_data)} групп, {len(tree)} факультетов.")
    return tree


def find_sub_groups(group_id: str) -> list[dict]:
    """Находит подгруппы для группы в дереве."""
    tree = fetch_groups_tree()
    if not tree:
        return []
    for fac in tree.values():
        for form in fac.values():
            for lvl in form.values():
                for crs in lvl.values():
                    for gn, meta in crs.items():
                        if isinstance(meta, dict) and str(meta.get("id")) == group_id:
                            return meta.get("sub_groups") or []
    return []


# ─── Расписание ───────────────────────────────────────────────────────────────

def fetch_schedule(group_id: str, sub_group_id: str | None = None,
                   date_from: date | None = None, date_to: date | None = None) -> list[dict]:
    """
    Загружает и кэширует расписание группы.
    По умолчанию — от начала текущей недели на 24 недели вперёд.
    """
    if date_from is None:
        today     = datetime.now(TZ).date()
        date_from = today - timedelta(days=today.weekday())
        date_to   = date_from + timedelta(weeks=24)

    cache_key = f"{group_id}:{sub_group_id or 0}:{date_from}:{date_to}"
    cached    = _schedule_cache.get(cache_key)
    if cached and (datetime.now() - cached["time"]).total_seconds() < CACHE_TTL_HOURS * 3600:
        return cached["lessons"]

    params: dict = {
        "group_id":   group_id,
        "start_date": date_from.isoformat(),
        "end_date":   date_to.isoformat(),
    }
    if sub_group_id and sub_group_id != "0":
        params["sub_group_id"] = sub_group_id

    items = api_get("schedule", params)
    if not isinstance(items, list):
        logger.warning(f"Пустой ответ расписания для группы {group_id}, возвращаем кэш.")
        return (cached or {}).get("lessons", [])

    # Батч-загрузка учителей, аудиторий, корпусов
    teacher_ids = {item["teacher_id"] for item in items if item.get("teacher_id")}
    room_ids    = {item["room_id"]    for item in items if item.get("room_id")}
    teachers    = _fetch_batch("teachers",  "teacher_ids",  teacher_ids)
    rooms       = _fetch_batch("rooms",     "room_ids",     room_ids)
    bld_ids     = {r.get("building_id") for r in rooms.values() if r.get("building_id")}
    buildings   = _fetch_batch("buildings", "building_ids", bld_ids)

    lessons = []
    for item in items:
        try:
            s = _parse_dt(item.get("start_time"))
            e = _parse_dt(item.get("end_time"))
            if not s or not e:
                continue
            lessons.append({
                "date":           s.date(),
                "time_start":     s.time(),
                "time_end":       e.time(),
                "time_start_str": s.strftime("%H:%M"),
                "time_end_str":   e.strftime("%H:%M"),
                "subject":        (item.get("name")  or "—").strip(),
                "type":           (item.get("type")  or "").strip(),
                "teacher":        _format_teacher(teachers.get(item.get("teacher_id"), {})),
                "room":           _format_room(rooms.get(item.get("room_id"), {}), buildings),
                "note":           (item.get("note")  or "").strip(),
            })
        except Exception as ex:
            logger.warning(f"Ошибка парсинга занятия: {ex}")

    lessons.sort(key=lambda l: (l["date"], l["time_start"]))
    _schedule_cache[cache_key] = {"lessons": lessons, "time": datetime.now()}
    return lessons


def invalidate_schedule(group_id: str):
    """Сбрасывает кэш расписания для группы."""
    keys_to_del = [k for k in _schedule_cache if k.startswith(f"{group_id}:")]
    for k in keys_to_del:
        del _schedule_cache[k]


# ─── Вспомогательные функции API ─────────────────────────────────────────────

def _fetch_batch(endpoint: str, param_name: str, ids: set) -> dict[int, dict]:
    """Загружает справочник батчем по списку ID."""
    valid = []
    for i in ids:
        try:
            valid.append(int(i))
        except (TypeError, ValueError):
            pass
    if not valid:
        return {}
    data = api_get(endpoint, {param_name: ",".join(map(str, valid))})
    if not isinstance(data, list):
        return {}
    return {int(item["id"]): item for item in data if item.get("id")}


def _parse_dt(value: str | None):
    """Парсит ISO datetime строку в datetime с МСК таймзоной."""
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except Exception:
        return None


_RANKS = [
    ("старш", "преп", "ст. преп."),
    ("завед", "каф",  "зав. каф."),
    ("проф",  None,   "проф."),
    ("доцент",None,   "доц."),
    ("ассист",None,   "асс."),
    ("препод",None,   "преп."),
]

def _format_teacher(data: dict) -> str:
    if not data:
        return ""
    raw  = (data.get("rank") or "").strip().lower()
    rank = ""
    for k1, k2, label in _RANKS:
        if k1 in raw and (k2 is None or k2 in raw):
            rank = label
            break
    if not rank and "." in (data.get("rank") or ""):
        rank = (data["rank"] or "").strip()
    name = (data.get("name") or "").strip()
    return f"{rank} {name}".strip() if rank else name


def _format_room(data: dict, buildings: dict) -> str:
    if not data:
        return ""
    room = (data.get("name") or "").strip()
    bld  = ""
    if data.get("building_id"):
        bld = buildings.get(int(data["building_id"]), {}).get("name", "")
    return f"{room}, {bld}" if room and bld else room or bld