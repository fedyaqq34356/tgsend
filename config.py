import os
from dotenv import load_dotenv


load_dotenv()

# Основные настройки
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # Обязательно укажите в .env

# Список ID пользователей с доступом (пустой = доступ всем)
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",") if os.getenv("ADMIN_IDS") else []

# Пути к файлам данных (с fallback)
ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", "data/accounts.json")
TARGETS_FILE = os.getenv("TARGETS_FILE", "data/targets.json")
SCHEDULED_FILE = os.getenv("SCHEDULED_FILE", "data/scheduled.json")
DRAFTS_FILE = os.getenv("DRAFTS_FILE", "data/drafts.json")
STATS_FILE = os.getenv("STATS_FILE", "data/stats.json")

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не указан в .env файле!")
