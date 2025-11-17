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
