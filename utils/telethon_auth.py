# utils/telethon_auth.py
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneCodeHashEmptyError,
)
from database.storage import storage
from datetime import datetime

# Хранилище активных процессов авторизации (user_id → данные)
auth_processes = {}

async def start_auth(user_id: int, session_name: str, api_id: int, api_hash: str, phone: str):
    """Начинает процесс авторизации: создаёт клиент и отправляет код."""
    try:
        client = TelegramClient(f"sessions/{session_name}", api_id, api_hash)
        await client.connect()
        await client.send_code_request(phone)

        auth_processes[user_id] = {
            "client": client,
            "phone": phone,
            "session_name": session_name,
            "api_id": api_id,
            "api_hash": api_hash,
        }

        return True, "Код отправлен на ваш Telegram."
    except Exception as e:
        return False, f"Ошибка отправки кода: {e}"

async def submit_code(user_id: int, raw_input: str):
    """
    Принимает ввод пользователя (цифры через пробел или слитно), собирает код и выполняет sign_in.
    Возвращает:
        - (True, сообщение) — успех
        - ("2fa", сообщение) — нужен пароль 2FA
        - ("retry", сообщение) — код истёк, отправлен новый
        - (False, сообщение) — ошибка
    """
    if user_id not in auth_processes:
        return False, "Процесс авторизации не найден."

    auth = auth_processes[user_id]
    client = auth["client"]
    phone = auth["phone"]

    # Извлекаем все цифры из ввода (игнорируем пробелы и другие символы)
    code = ''.join(char for char in raw_input if char.isdigit())
    
    # Проверяем длину кода
    if len(code) != 5:
        return False, f"Код должен состоять ровно из 5 цифр. Получено: {len(code)} цифр(ы).\nПопробуйте снова."

    try:
        await client.sign_in(phone, code=code)

        # Успешная авторизация
        storage.accounts[auth["session_name"]] = {
            "api_id": auth["api_id"],
            "api_hash": auth["api_hash"],
            "phone": phone,
            "client": client,
        }
        storage.save_accounts()
        del auth_processes[user_id]

        return True, f"✅ Аккаунт '{auth['session_name']}' успешно добавлен!"

    except PhoneCodeExpiredError:
        # Код истёк — запрашиваем новый автоматически
        await client.send_code_request(phone)
        return "retry", "⏰ Код истёк. Новый код отправлен на ваш Telegram.\n\n💡 Введите новый код (5 цифр через пробел):"

    except PhoneCodeInvalidError:
        return False, "❌ Неверный код. Попробуйте снова."

    except SessionPasswordNeededError:
        return "2fa", "🔐 Требуется пароль двухфакторной аутентификации:"

    except Exception as e:
        return False, f"❌ Неизвестная ошибка: {e}"

async def submit_password(user_id: int, password: str):
    """Завершает авторизацию с 2FA паролем."""
    if user_id not in auth_processes:
        return False, "Процесс авторизации не найден."

    auth = auth_processes[user_id]
    client = auth["client"]

    try:
        await client.sign_in(password=password.strip())

        storage.accounts[auth["session_name"]] = {
            "api_id": auth["api_id"],
            "api_hash": auth["api_hash"],
            "phone": auth["phone"],
            "client": client,
        }
        storage.save_accounts()
        del auth_processes[user_id]

        return True, f"✅ Аккаунт '{auth['session_name']}' успешно добавлен!"
    except Exception as e:
        return False, f"❌ Ошибка 2FA: {e}"

async def cancel_auth(user_id: int):
    """Отменяет процесс авторизации и закрывает клиент."""
    if user_id in auth_processes:
        try:
            await auth_processes[user_id]["client"].disconnect()
        except:
            pass
        del auth_processes[user_id]

async def send_telegram_message(client, target_data, text, account_name, media_type="text", file_id=None):
    """Отправка сообщения через указанный аккаунт с поддержкой медиа"""
    try:
        if not client.is_connected():
            await client.connect()

        # Определяем получателя
        if target_data["type"] == "user":
            recipient = target_data["username"]
            target_name = f"@{target_data['username']}"
        else:
            recipient = int(target_data["chat_id"])
            target_name = f"Группа {target_data['chat_id']}"

        # Отправка в зависимости от типа контента
        if media_type == "text":
            await client.send_message(recipient, text)
        elif media_type == "photo" and file_id:
            await client.send_file(recipient, file_id, caption=text)
        elif media_type == "video" and file_id:
            await client.send_file(recipient, file_id, caption=text)
        elif media_type == "document" and file_id:
            await client.send_file(recipient, file_id, caption=text)
        else:
            # Fallback на текст
            await client.send_message(recipient, text)

        # Статистика
        storage.stats["sent"] = storage.stats.get("sent", 0) + 1
        storage.stats["last_send"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if account_name not in storage.account_stats:
            storage.account_stats[account_name] = {"sent": 0, "history": []}

        storage.account_stats[account_name]["sent"] += 1
        
        display_text = text[:50] + "..." if len(text) > 50 else text
        if media_type != "text":
            display_text = f"[{media_type.upper()}] {display_text}"
        
        storage.account_stats[account_name]["history"].append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target": target_name,
            "text": display_text
        })

        if len(storage.account_stats[account_name]["history"]) > 100:
            storage.account_stats[account_name]["history"] = storage.account_stats[account_name]["history"][-100:]

        storage.save_stats()
        return True
    except Exception as e:
        print(f"Ошибка отправки от {account_name}: {e}")
        return False
