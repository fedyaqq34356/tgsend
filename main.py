# main.py (bot.py)
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.storage import storage
from handlers import start, accounts, targets, messages, drafts, scheduler, stats, assignments

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

async def scheduler_task():
    """Фоновая задача для проверки запланированных сообщений"""
    from datetime import datetime
    import random
    from utils.telethon_auth import send_telegram_message
    
    while True:
        await asyncio.sleep(30)
        
        now = datetime.now()
        to_remove = []
        
        for msg in storage.scheduled_messages:
            try:
                send_time = datetime.strptime(msg["time"], "%Y-%m-%d %H:%M:%S")
                
                if now >= send_time:
                    target_id = msg["target_id"]
                    if target_id in storage.targets:
                        target_data = storage.targets[target_id]
                        assigned = msg["accounts"].copy()
                        
                        if not assigned:
                            assigned = [random.choice(list(storage.accounts.keys()))] if storage.accounts else []
                        
                        for acc_name in assigned:
                            if acc_name in storage.accounts:
                                client = storage.accounts[acc_name]["client"]
                                await send_telegram_message(client, target_data, msg["text"], acc_name)
                                await asyncio.sleep(2)
                    
                    to_remove.append(msg)
            except Exception as e:
                print(f"Ошибка планировщика: {e}")
                to_remove.append(msg)
        
        for msg in to_remove:
            storage.scheduled_messages.remove(msg)
        
        if to_remove:
            storage.save_scheduled()

async def main():
    # Загружаем данные
    storage.load_all()
    
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
    dp.include_router(start.router)  # Start должен быть последним!
    
    # Запускаем планировщик
    asyncio.create_task(scheduler_task())
    
    # Запускаем бота
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())