# utils/telethon_auth.py
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from database.storage import storage
from datetime import datetime

# Хранилище процессов авторизации
auth_processes = {}

async def start_auth(user_id, session_name, api_id, api_hash, phone):
    """Начинает процесс авторизации"""
    try:
        client = TelegramClient(f"sessions/{session_name}", int(api_id), api_hash)
        await client.connect()
        
        # Отправляем запрос кода
        await client.send_code_request(phone)
        
        auth_processes[user_id] = {
            "client": client,
            "phone": phone,
            "session_name": session_name,
            "api_id": int(api_id),
            "api_hash": api_hash,
            "waiting_for": "code"
        }
        
        return True, "Код отправлен на ваш Telegram. Введите его:"
    except Exception as e:
        return False, f"Ошибка: {e}"

async def submit_code(user_id, code):
    """Отправляет код подтверждения"""
    if user_id not in auth_processes:
        return False, "Процесс авторизации не найден"
    
    auth = auth_processes[user_id]
    client = auth["client"]
    phone = auth["phone"]
    
    try:
        await client.sign_in(phone, code.strip())
        
        # Успешная авторизация
        storage.accounts[auth["session_name"]] = {
            "api_id": auth["api_id"],
            "api_hash": auth["api_hash"],
            "phone": phone,
            "client": client
        }
        
        storage.save_accounts()
        del auth_processes[user_id]
        
        return True, f"✅ Аккаунт '{auth['session_name']}' успешно добавлен!"
        
    except SessionPasswordNeededError:
        # Нужен 2FA пароль
        auth["waiting_for"] = "password"
        return "2fa", "Требуется пароль двухфакторной аутентификации:"
        
    except Exception as e:
        return False, f"Ошибка: {e}"

async def submit_password(user_id, password):
    """Отправляет 2FA пароль"""
    if user_id not in auth_processes:
        return False, "Процесс авторизации не найден"
    
    auth = auth_processes[user_id]
    client = auth["client"]
    
    try:
        await client.sign_in(password=password.strip())
        
        # Успешная авторизация
        storage.accounts[auth["session_name"]] = {
            "api_id": auth["api_id"],
            "api_hash": auth["api_hash"],
            "phone": auth["phone"],
            "client": client
        }
        
        storage.save_accounts()
        del auth_processes[user_id]
        
        return True, f"✅ Аккаунт '{auth['session_name']}' успешно добавлен!"
        
    except Exception as e:
        return False, f"Ошибка: {e}"

async def cancel_auth(user_id):
    """Отменяет процесс авторизации"""
    if user_id in auth_processes:
        try:
            await auth_processes[user_id]["client"].disconnect()
        except:
            pass
        del auth_processes[user_id]

async def send_telegram_message(client, target_data, text, account_name):
    """Отправляет сообщение через Telethon"""
    try:
        if not client.is_connected():
            await client.connect()
        
        if target_data["type"] == "user":
            await client.send_message(target_data["username"], text)
            target_name = f"@{target_data['username']}"
        else:
            chat_id = int(target_data["chat_id"])
            await client.send_message(chat_id, text)
            target_name = f"Группа {target_data['chat_id']}"
        
        # Обновляем статистику
        storage.stats["sent"] = storage.stats.get("sent", 0) + 1
        storage.stats["last_send"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if account_name not in storage.account_stats:
            storage.account_stats[account_name] = {"sent": 0, "history": []}
        
        storage.account_stats[account_name]["sent"] += 1
        storage.account_stats[account_name]["history"].append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target": target_name,
            "text": text[:50] + "..." if len(text) > 50 else text
        })
        
        # Ограничиваем историю
        if len(storage.account_stats[account_name]["history"]) > 100:
            storage.account_stats[account_name]["history"] = storage.account_stats[account_name]["history"][-100:]
        
        storage.save_stats()
        
        return True
    except Exception as e:
        print(f"Ошибка отправки от {account_name}: {e}")
        return False