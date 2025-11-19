import os
from typing import List

# ==================== ОСНОВНЫЕ НАСТРОЙКИ ====================

# Обязательный токен бота — задаётся в Variables на Railway
BOT_TOKEN: str = os.getenv("BOT_TOKEN")
if not BOTЕН:
    raise ValueError("BOT_TOKEN не указан! Добавьте переменную BOT_TOKEN в разделе Variables на Railway.")

# Список админов (через запятую, без пробелов: 123456789,987654321)
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = (
    [int(uid.strip()) for uid in admin_ids_raw.split(",") if uid.strip()]
    if admin_ids_raw
    else []
)

# ==================== ПУТИ К ФАЙЛАМ ====================
# На Railway файловую систему лучше держать в /app или в переменной
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Можно переопределить пути через переменные окружения, если нужно
ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", os.path.join(BASE_DIR, "data", "accounts.json"))
TARGETS_FILE = os.getenv("TARGETS_FILE", os.path.join(BASE_DIR, "data", "targets.json"))
SCHEDULED_FILE = os.getenv("SCHEDULED_FILE", os.path.join(BASE_DIR, "data", "scheduled.json"))
DRAFTS_FILE = os.getenv("DRAFTS_FILE", os.path.join(BASE_DIR, "data", "drafts.json"))
STATS_FILE = os.getenv("STATS_FILE", os.path.join(BASE_DIR, "data", "stats.json"))

# ==================== АВТО-СОЗДАНИЕ ПАПОК ====================
os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(SCHEDULED_FILE), exist_ok=True)
os.makedirs(os.path.dirname(DRAFTS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

# ==================== ДОПОЛНИТЕЛЬНЫЕ ПЕРЕМЕННЫЕ (по желанию) ====================
# Пример дополнительных переменных, которые удобно задавать на Railway
DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Если используете прокси или другие настройки — добавляйте аналогично
# PROXY_URL = os.getenv("PROXY_URL")
