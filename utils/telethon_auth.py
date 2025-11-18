# utils/telethon_auth.py
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneCodeHashEmptyError,
)
from telethon.tl.types import KeyboardButtonUrl
from aiogram.types import InlineKeyboardMarkup
from database.storage import storage
from datetime import datetime
import os
import traceback

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
    if user_id not in auth_processes:
        return False, "Процесс авторизации не найден."

    auth = auth_processes[user_id]
    client = auth["client"]
    phone = auth["phone"]

    code = ''.join(char for char in raw_input if char.isdigit())
    if len(code) != 5:
        return False, f"Код должен состоять ровно из 5 цифр. Получено: {len(code)}.\nПопробуйте снова."

    try:
        await client.sign_in(phone, code=code)

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
        await client.send_code_request(phone)
        return "retry", "⏰ Код истёк. Новый код отправлен.\nВведите новый код (5 цифр через пробел):"
    except PhoneCodeInvalidError:
        return False, "❌ Неверный код. Попробуйте снова."
    except SessionPasswordNeededError:
        return "2fa", "🔐 Требуется пароль двухфакторной аутентификации:"
    except Exception as e:
        return False, f"❌ Неизвестная ошибка: {e}"


async def submit_password(user_id: int, password: str):
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
    if user_id in auth_processes:
        try:
            await auth_processes[user_id]["client"].disconnect()
        except:
            pass
        del auth_processes[user_id]


async def send_telegram_message(
    client,
    target_data: dict,
    text: str,
    account_name: str,
    media_type: str = "text",
    file_id: str = None,
    bot = None,
    reply_markup: InlineKeyboardMarkup = None
) -> bool:
    """
    Универсальная отправка сообщения через Telethon.
    Поддерживает: текст (HTML), медиа, inline-кнопки (URL).
    """
    try:
        if not await client.is_connected():
            await client.connect()

        # Получатель
        recipient = target_data["username"] if target_data["type"] == "user" else int(target_data["chat_id"])
        target_display = f"@{target_data['username']}" if target_data["type"] == "user" else f"чат {target_data['chat_id']}"

        # Преобразуем aiogram-кнопки в Telethon-кнопки
        buttons = None
        if reply_markup:
            telethon_buttons = []
            for row in reply_markup.inline_keyboard:
                telethon_row = []
                for btn in row:
                    if btn.url:
                        telethon_row.append(KeyboardButtonUrl(btn.text, btn.url))
                if telethon_row:
                    telethon_buttons.append(telethon_row)
            buttons = telethon_buttons if telethon_buttons else None

        # Отправка
        if media_type == "text" and text:
            await client.send_message(
                recipient,
                text,
                parse_mode="html",
                link_preview=False,
                buttons=buttons
            )
        elif media_type in ("photo", "video", "document") and file_id and bot:
            os.makedirs("temp_media", exist_ok=True)
            ext = ".jpg" if media_type == "photo" else ".mp4" if media_type == "video" else ""
            file_path = f"temp_media/{file_id}{ext}"

            await bot.download(file_id, destination=file_path)

            await client.send_file(
                recipient,
                file_path,
                caption=text or None,
                parse_mode="html" if text else None,
                buttons=buttons
            )

            try:
                os.remove(file_path)
            except OSError:
                pass
        else:
            await client.send_message(
                recipient,
                text or "Сообщение отправлено",
                parse_mode="html" if text else None,
                buttons=buttons
            )

        # ─────── Статистика ───────
        storage.stats["sent"] = storage.stats.get("sent", 0) + 1
        storage.stats["last_send"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if account_name not in storage.account_stats:
            storage.account_stats[account_name] = {"sent": 0, "history": []}

        storage.account_stats[account_name]["sent"] += 1

        short_text = (text or "[медиа]")[:50]
        if len(text or "") > 50:
            short_text += "..."

        storage.account_stats[account_name]["history"].append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target": target_display,
            "text": short_text
        })

        if len(storage.account_stats[account_name]["history"]) > 100:
            storage.account_stats[account_name]["history"] = storage.account_stats[account_name]["history"][-100:]

        storage.save_stats()
        return True

    except Exception as e:
        print(f"[ERROR] Ошибка отправки от {account_name} → {target_display}: {e}")
        traceback.print_exc()
        return False
