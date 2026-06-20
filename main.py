# main.py (bot
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

async def scheduler_task(bot):
    """Фоновая задача для проверки запланированных сообщений"""
    from datetime import datetime
    import random
    from utils.telethon_auth import send_telegram_message
    
    print("⏰ Планировщик запущен!")
    
    while True:
        try:
            await asyncio.sleep(30) 
            
            if not storage.scheduled_messages:
                continue
            
            now = datetime.now()
            print(f"🔍 Проверка запланированных ({len(storage.scheduled_messages)} шт.) - {now.strftime('%H:%M:%S')}")
            
            to_remove = []
            
            for msg in storage.scheduled_messages:
                try:
                    send_time = datetime.strptime(msg["time"], "%Y-%m-%d %H:%M:%S")
                    
                    print(f"  📅 Сообщение на {send_time.strftime('%d.%m %H:%M')} (осталось: {(send_time - now).total_seconds():.0f} сек)")
                    
                    # Проверяем, пришло ли время отправки
                    if now >= send_time:
                        print(f"⏰ ⚡ ВРЕМЯ ПРИШЛО! Отправка: {msg.get('text', '[Медиа]')[:30]}...")
                        
                        target_id = msg["target_id"]
                        
                        if target_id not in storage.targets:
                            print(f"❌ Получатель {target_id} не найден!")
                            to_remove.append(msg)
                            continue
                        
                        target_data = storage.targets[target_id]
                        assigned = msg.get("accounts", []).copy()
                        
                        # Если аккаунты не указаны, используем назначенные или случайный
                        if not assigned:
                            assigned = target_data.get("assigned_accounts", []).copy()
                        
                        if not assigned and storage.accounts:
                            assigned = [random.choice(list(storage.accounts.keys()))]
                        
                        if not assigned:
                            print("❌ Нет доступных аккаунтов для отправки!")
                            to_remove.append(msg)
                            continue
                        
                        success_count = 0
                        for acc_name in assigned:
                            if acc_name in storage.accounts:
                                client = storage.accounts[acc_name]["client"]
                                
                                # Проверяем подключение
                                if not client.is_connected():
                                    print(f"🔌 Подключение {acc_name}...")
                                    await client.connect()
                                
                                # Отправляем сообщение
                                success = await send_telegram_message(
                                    client, 
                                    target_data, 
                                    msg.get("text", ""), 
                                    acc_name,
                                    media_type=msg.get("content_type", "text"),
                                    file_id=msg.get("file_id"),
                                    bot=bot
                                )
                                
                                if success:
                                    success_count += 1
                                    print(f"✅ Отправлено через {acc_name}")
                                else:
                                    print(f"❌ Ошибка отправки через {acc_name}")
                                
                                await asyncio.sleep(2)  # Задержка между отправками
                            else:
                                print(f"⚠️ Аккаунт {acc_name} не найден")
                        
                        print(f"📊 Итого отправлено: {success_count}/{len(assigned)}")
                        to_remove.append(msg)
                
                except Exception as e:
                    print(f"❌ Ошибка обработки сообщения: {e}")
                    import traceback
                    traceback.print_exc()
                    to_remove.append(msg)
            
            # Удаляем отправленные сообщения
            if to_remove:
                for msg in to_remove:
                    if msg in storage.scheduled_messages:
                        storage.scheduled_messages.remove(msg)
                storage.save_scheduled()
                print(f"🗑 Удалено {len(to_remove)} выполненных задач")
        
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА планировщика: {e}")
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
    dp.include_router(start.router)  # Start должен быть последним!
    
    # Запускаем планировщик с объектом bot
    asyncio.create_task(scheduler_task(bot))
    
    # Запускаем бота
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
