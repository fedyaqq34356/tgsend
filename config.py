import os
from typing import List




BOT_TOKEN: str = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не указан! Добавьте переменную BOT_TOKEN в разделе Variables на Railway.")


admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = (
    [int(uid.strip()) for uid in admin_ids_raw.split(",") if uid.strip()]
    if admin_ids_raw
    else []
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", os.path.join(BASE_DIR, "data", "accounts.json"))
TARGETS_FILE = os.getenv("TARGETS_FILE", os.path.join(BASE_DIR, "data", "targets.json"))
SCHEDULED_FILE = os.getenv("SCHEDULED_FILE", os.path.join(BASE_DIR, "data", "scheduled.json"))
DRAFTS_FILE = os.getenv("DRAFTS_FILE", os.path.join(BASE_DIR, "data", "drafts.json"))
STATS_FILE = os.getenv("STATS_FILE", os.path.join(BASE_DIR, "data", "stats.json"))

os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(SCHEDULED_FILE), exist_ok=True)
os.makedirs(os.path.dirname(DRAFTS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
