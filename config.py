import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN        = os.getenv("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")
TZ               = ZoneInfo("Europe/Moscow")
DB_FILE          = "bot.db"
ADMIN_IDS: set   = {7610286525}
EVENING_HOUR     = 20          # Час вечерней рассылки по МСК

API_BASE         = "https://api.herzen.spb.ru/schedule/v1"
CACHE_TTL_HOURS  = 1           # Кэш расписания
GROUPS_TTL_HOURS = 24          # Кэш дерева групп

FAC_PAGE_SIZE    = 8
GRP_PAGE_SIZE    = 10