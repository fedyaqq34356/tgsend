# main.py (bot.py)
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.storage import storage
from handlers import start, accounts, targets, messages, drafts, scheduler, stats, assignments, button_message

logging.basicConfig(level=logging.INFO)

async def connect_accounts():
    """Подключает все сохраненные аккаунты"""
    print("🔄 Подключение аккаунтов...")
    for name, acc in storage.accounts.items():
        try:
            client = acc["client"]
            if not client.is_connected():
                await client.connect()
            if not await client.is_user_authorized():
                print(f"⚠️ {name} требует повторной авторизации")
            else:
                print(f"✅ {name} подключен")
        except Exception as e:
            print(f"❌ Ошибка подключения {name}: {e}")

async def scheduler_task(bot):
    """Фоновая задача: проверяет и отправляет запланированные сообщения"""
    from datetime import datetime
    import random
    from aiogram.types import InlineKeyboardMarkup
    from utils.telethon_auth import send_telegram_message

    print("⏰ Планировщик запущен и работает в фоновом режиме.")

    while True:
        try:
            await asyncio.sleep(30)  # Проверка каждые 30 секунд

            if not storage.scheduled_messages:
                continue

            now = datetime.now()
            to_remove = []

            for msg in storage.scheduled_messages[:]:  # копия списка, чтобы безопасно удалять
                try:
                    send_time = datetime.strptime(msg["time"], "%Y-%m-%d %H:%M:%S")

                    if now >= send_time:
                        print(f"⏰ Отправка запланированного сообщения: {send_time.strftime('%d.%m %H:%M')}")

                        target_id = msg["target_id"]
                        if target_id not in storage.targets:
                            print(f"❌ Получатель {target_id} удалён — пропускаем")
                            to_remove.append(msg)
                            continue

                        target_data = storage.targets[target_id]

                        # Определяем аккаунты для отправки
                        assigned_accounts = msg.get("accounts", []) or target_data.get("assigned_accounts", [])
                        if not assigned_accounts and storage.accounts:
                            assigned_accounts = [random.choice(list(storage.accounts.keys()))]

                        if not assigned_accounts:
                            print("❌ Нет доступных аккаунтов для отправки!")
                            to_remove.append(msg)
                            continue

                        # Подготовка клавиатуры (если есть)
                        reply_markup = None
                        if msg.get("reply_markup"):
                            reply_markup = InlineKeyboardMarkup(**msg["reply_markup"])

                        success_count = 0
                        for acc_name in assigned_accounts:
                            if acc_name not in storage.accounts:
                                continue

                            client = storage.accounts[acc_name]["client"]

                            # Подключаемся, если нужно
                            if not client.is_connected():
                                try:
                                    await client.connect()
                                except Exception as e:
                                    print(f"⚠️ Не удалось подключить {acc_name}: {e}")
                                    continue

                            # Отправляем
                            success = await send_telegram_message(
                                client=client,
                                target_data=target_data,
                                text=msg.get("text", ""),
                                account_name=acc_name,
                                media_type=msg.get("content_type", "text"),
                                file_id=msg.get("file_id"),
                                bot=bot,
                                reply_markup=reply_markup
                            )

                            if success:
                                success_count += 1
                                print(f"✅ Отправлено через {acc_name}")
                            else:
                                print(f"❌ Ошибка при отправке через {acc_name}")

                            await asyncio.sleep(2)  # Защита от флуда

                        print(f"📊 Запланированное сообщение отправлено: {success_count}/{len(assigned_accounts)}")
                        to_remove.append(msg)

                except Exception as e:
                    print(f"❌ Ошибка обработки запланированного сообщения: {e}")
                    import traceback
                    traceback.print_exc()
                    to_remove.append(msg)

            # Удаляем отправленные/ошибочные задачи
            if to_remove:
                for msg in to_remove:
                    if msg in storage.scheduled_messages:
                        storage.scheduled_messages.remove(msg)
                storage.save_scheduled()
                print(f"🗑 Удалено {len(to_remove)} выполненных/ошибочных задач")

        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в планировщике: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(10)

async def main():
    # Загружаем данные
    storage.load_all()
    print(f"📂 Загружено: {len(storage.accounts)} аккаунтов, {len(storage.targets)} получателей, {len(storage.scheduled_messages)} запланированных")
    
    # Подключаем аккаунты
    await connect_accounts()
    
    # Создаем бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # ВАЖНО: Порядок регистрации роутеров имеет значение!
    # Сначала роутеры с конкретными состояниями, потом общие
    dp.include_router(accounts.router)
    dp.include_router(targets.router)
    dp.include_router(messages.router)
    dp.include_router(drafts.router)
    dp.include_router(scheduler.router)
    dp.include_router(assignments.router)
    dp.include_router(stats.router)
    dp.include_router(button_message.router)
    dp.include_router(start.router)  # Start должен быть последним!
    
    # Запускаем планировщик с объектом bot
    asyncio.create_task(scheduler_task(bot))
    
    # Запускаем бота
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
