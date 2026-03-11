"""
Работа с SQLite базой данных.
Хранит настройки пользователей: группа, подгруппа, уведомления, язык.
"""

import sqlite3
import logging
from config import DB_FILE
from texts import TEXTS

logger = logging.getLogger(__name__)

_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id        INTEGER PRIMARY KEY,
                group_id       TEXT,
                group_name     TEXT,
                sub_group_id   TEXT,
                sub_group_name TEXT,
                notify         INTEGER DEFAULT 0,
                evening        INTEGER DEFAULT 0,
                lang           TEXT    DEFAULT 'ru'
            )
        """)
        _conn.commit()
        logger.info("SQLite DB инициализирована.")
    return _conn


def get_user(user_id: int) -> sqlite3.Row | None:
    return get_conn().execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()


def set_user(user_id: int, **kwargs):
    """Создаёт запись если нет, обновляет переданные поля."""
    if get_user(user_id) is None:
        get_conn().execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    if kwargs:
        cols = ", ".join(f"{k} = ?" for k in kwargs)
        get_conn().execute(
            f"UPDATE users SET {cols} WHERE user_id = ?",
            (*kwargs.values(), user_id)
        )
    get_conn().commit()


def get_attr(user_id: int, key: str, default=None):
    row = get_user(user_id)
    if row is None:
        return default
    val = row[key]
    return val if val is not None else default


def all_users() -> list[sqlite3.Row]:
    return get_conn().execute("SELECT * FROM users").fetchall()


# ── Удобные геттеры ───────────────────────────────────────────────────────────

def get_group_id(user_id: int) -> str | None:
    return get_attr(user_id, "group_id")


def get_group_label(user_id: int) -> str:
    return get_attr(user_id, "group_name") or get_attr(user_id, "group_id") or "—"


def get_lang(user_id: int) -> str:
    return get_attr(user_id, "lang", "ru")


def t(user_id: int, key: str) -> str:
    """Возвращает перевод для пользователя."""
    lang = get_lang(user_id)
    return TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"].get(key, key))
