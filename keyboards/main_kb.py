# keyboards/main_kb.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    kb = [
        [KeyboardButton(text="📱 Аккаунты"), KeyboardButton(text="👥 Получатели")],
        [KeyboardButton(text="✉️ Отправить"), KeyboardButton(text="📝 Черновики")],
        [KeyboardButton(text="⏰ Планирование"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🔗 Назначения"), KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def accounts_menu():
    kb = [
        [KeyboardButton(text="➕ Добавить аккаунт")],
        [KeyboardButton(text="📋 Список аккаунтов")],
        [KeyboardButton(text="🗑 Удалить аккаунт")],
        [KeyboardButton(text="◀️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def targets_menu():
    kb = [
        [KeyboardButton(text="➕ Добавить получателя")],
        [KeyboardButton(text="📋 Список получателей")],
        [KeyboardButton(text="◀️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def drafts_menu():
    kb = [
        [KeyboardButton(text="➕ Создать черновик")],
        [KeyboardButton(text="📋 Список черновиков")],
        [KeyboardButton(text="⚙️ Настроить черновик")],
        [KeyboardButton(text="📤 Отправить черновик")],
        [KeyboardButton(text="🗑 Удалить черновик")],
        [KeyboardButton(text="◀️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def scheduler_menu():
    kb = [
        [KeyboardButton(text="➕ Запланировать")],
        [KeyboardButton(text="📋 Показать запланированные")],
        [KeyboardButton(text="🗑 Удалить запланированное")],
        [KeyboardButton(text="◀️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def stats_menu():
    kb = [
        [KeyboardButton(text="📊 Общая статистика")],
        [KeyboardButton(text="📱 Статистика по аккаунтам")],
        [KeyboardButton(text="◀️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def assignments_menu():
    kb = [
        [KeyboardButton(text="🔗 Назначить аккаунт")],
        [KeyboardButton(text="❌ Удалить назначение")],
        [KeyboardButton(text="◀️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def content_type_kb():
    """Клавиатура выбора типа контента"""
    kb = [
        [KeyboardButton(text="💬 Текст")],
        [KeyboardButton(text="🖼 Фото"), KeyboardButton(text="🎥 Видео")],
        [KeyboardButton(text="📎 Файл")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def cancel_kb():
    kb = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
