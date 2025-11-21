# handlers/messages.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import SendMessage
from keyboards.main_kb import cancel_kb, main_menu, content_type_kb
from database.storage import storage
from utils.telethon_auth import send_telegram_message
import random
import asyncio

router = Router()

@router.message(F.text == "✉️ Отправить")
async def send_message_start(message: Message, state: FSMContext):
    if not storage.targets:
        await message.answer("❌ Сначала добавьте получателей!", reply_markup=main_menu())
        return
    
    if not storage.accounts:
        await message.answer("❌ Сначала добавьте аккаунты!", reply_markup=main_menu())
        return
    
    await state.set_state(SendMessage.choosing_targets)
    
    text = "Выберите получателей (номера через запятую или 'all'):\n\n"
    target_list = list(storage.targets.items())
    for i, (tid, data) in enumerate(target_list, 1):
        if data["type"] == "user":
            text += f"{i}. @{data['username']}\n"
        else:
            text += f"{i}. Группа {data['chat_id']}\n"
    
    text += "\nПример: 1,3,5 или all"
    await message.answer(text, reply_markup=cancel_kb())

@router.message(SendMessage.choosing_targets, F.text == "❌ Отмена")
async def cancel_targets(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=main_menu())

@router.message(SendMessage.choosing_targets)
async def process_targets_choice(message: Message, state: FSMContext):
    try:
        target_list = list(storage.targets.keys())
        
        if message.text.lower() == "all":
            selected_targets = target_list.copy()
        else:
            indices = [int(x.strip()) - 1 for x in message.text.split(',') if x.strip().isdigit()]
            selected_targets = [target_list[i] for i in indices if 0 <= i < len(target_list)]
        
        if not selected_targets:
            await message.answer("❌ Получатели не выбраны! Попробуйте снова:")
            return
        
        await state.update_data(target_ids=selected_targets)
        await state.set_state(SendMessage.choosing_send_mode)
        await message.answer(
            f"✅ Выбрано получателей: {len(selected_targets)}\n\n"
            "Как отправить?\n\n"
            "1️⃣ - Все одновременно\n"
            "2️⃣ - По очереди с интервалом\n\n"
            "Отправьте 1 или 2:",
            reply_markup=cancel_kb()
        )
    except:
        await message.answer("❌ Ошибка! Попробуйте снова:")

@router.message(SendMessage.choosing_send_mode, F.text == "❌ Отмена")
async def cancel_send_mode(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=main_menu())

@router.message(SendMessage.choosing_send_mode, F.text.in_(["1", "2"]))
async def process_send_mode(message: Message, state: FSMContext):
    if message.text == "1":
        await state.update_data(send_mode="instant")
        await state.set_state(SendMessage.waiting_content_type)
        await message.answer("Что отправить?", reply_markup=content_type_kb())
    else:
        await state.update_data(send_mode="delayed")
        await state.set_state(SendMessage.waiting_interval)
        await message.answer(
            "Установите интервал между отправками:\n\n"
            "Отправьте число (в секундах):\n"
            "Примеры:\n"
            "• 30 - каждые 30 секунд\n"
            "• 300 - каждые 5 минут\n"
            "• 600 - каждые 10 минут\n"
            "• 1800 - каждые 30 минут",
            reply_markup=cancel_kb()
        )

@router.message(SendMessage.waiting_interval, F.text == "❌ Отмена")
async def cancel_interval(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=main_menu())

@router.message(SendMessage.waiting_interval)
async def process_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        if interval < 5:
            await message.answer("❌ Минимальный интервал 5 секунд! Попробуйте снова:")
            return
        await state.update_data(interval=interval)
        await state.set_state(SendMessage.waiting_content_type)
        await message.answer("Что отправить?", reply_markup=content_type_kb())
    except:
        await message.answer("❌ Введите число в секундах! Попробуйте снова:")

@router.message(SendMessage.waiting_content_type, F.text == "❌ Отмена")
async def cancel_content_type(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=main_menu())

@router.message(SendMessage.waiting_content_type)
async def process_content_type(message: Message, state: FSMContext):
    content_type = message.text
    
    if content_type == "💬 Текст":
        await state.update_data(content_type="text")
        await state.set_state(SendMessage.waiting_text)
        await message.answer("Введите текст сообщения:", reply_markup=cancel_kb())
    elif content_type == "🖼 Фото":
        await state.update_data(content_type="photo")
        await state.set_state(SendMessage.waiting_media)
        await message.answer("Отправьте фото (можно с подписью):", reply_markup=cancel_kb())
    elif content_type == "🎥 Видео":
        await state.update_data(content_type="video")
        await state.set_state(SendMessage.waiting_media)
        await message.answer("Отправьте видео (можно с подписью):", reply_markup=cancel_kb())
    elif content_type == "📎 Файл":
        await state.update_data(content_type="document")
        await state.set_state(SendMessage.waiting_media)
        await message.answer("Отправьте файл (можно с подписью):", reply_markup=cancel_kb())
    else:
        await message.answer("❌ Выберите тип из кнопок!")

@router.message(SendMessage.waiting_text, F.text == "❌ Отмена")
async def cancel_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=main_menu())

@router.message(SendMessage.waiting_text)
async def process_message_text(message: Message, state: FSMContext):
    data = await state.get_data()
    target_ids = data["target_ids"]
    send_mode = data.get("send_mode", "instant")
    
    if message.html_text:
        text = message.html_text
    else:
        text = message.text
    
    await state.clear()
    
    if send_mode == "instant":
        await message.answer(f"📤 Отправка {len(target_ids)} получателям...")
        success_count = 0
        for target_id in target_ids:
            if target_id in storage.targets:
                target_data = storage.targets[target_id]
                assigned = target_data.get("assigned_accounts", []).copy()
                
                if not assigned:
                    assigned = [random.choice(list(storage.accounts.keys()))] if storage.accounts else []
                
                for acc_name in assigned:
                    if acc_name in storage.accounts:
                        client = storage.accounts[acc_name]["client"]
                        success = await send_telegram_message(
                            client, target_data, text, acc_name, 
                            media_type="text", bot=message.bot
                        )
                        if success:
                            success_count += 1
                        await asyncio.sleep(2)
        
        await message.answer(
            f"✅ Готово! Отправлено: {success_count}",
            reply_markup=main_menu()
        )
    else:
        interval = data.get("interval", 300)
        await message.answer(
            f"📤 Отправка начата!\n"
            f"Получателей: {len(target_ids)}\n"
            f"Интервал: {interval} сек ({interval//60} мин)\n\n"
            f"Сообщения отправляются в фоне...",
            reply_markup=main_menu()
        )
        asyncio.create_task(send_with_interval(target_ids, text, interval, "text", None, message.bot))

@router.message(SendMessage.waiting_media, F.text == "❌ Отмена")
async def cancel_media(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=main_menu())

@router.message(SendMessage.waiting_media)
async def process_message_media(message: Message, state: FSMContext):
    data = await state.get_data()
    target_ids = data["target_ids"]
    send_mode = data.get("send_mode", "instant")
    content_type = data["content_type"]
    caption = message.caption or ""
    
    file_id = None
    if content_type == "photo" and message.photo:
        file_id = message.photo[-1].file_id
    elif content_type == "video" and message.video:
        file_id = message.video.file_id
    elif content_type == "document" and message.document:
        file_id = message.document.file_id
    
    if not file_id:
        await message.answer("❌ Не удалось получить медиа! Попробуйте снова:")
        return
    
    await state.clear()
    
    if send_mode == "instant":
        await message.answer(f"📤 Отправка {len(target_ids)} получателям...")
        success_count = 0
        for target_id in target_ids:
            if target_id in storage.targets:
                target_data = storage.targets[target_id]
                assigned = target_data.get("assigned_accounts", []).copy()
                
                if not assigned:
                    assigned = [random.choice(list(storage.accounts.keys()))] if storage.accounts else []
                
                for acc_name in assigned:
                    if acc_name in storage.accounts:
                        client = storage.accounts[acc_name]["client"]
                        success = await send_telegram_message(
                            client, target_data, caption, acc_name,
                            media_type=content_type, file_id=file_id, bot=message.bot
                        )
                        if success:
                            success_count += 1
                        await asyncio.sleep(2)
        
        await message.answer(
            f"✅ Готово! Отправлено: {success_count}",
            reply_markup=main_menu()
        )
    else:
        interval = data.get("interval", 300)
        await message.answer(
            f"📤 Отправка начата!\n"
            f"Получателей: {len(target_ids)}\n"
            f"Интервал: {interval} сек ({interval//60} мин)\n\n"
            f"Сообщения отправляются в фоне...",
            reply_markup=main_menu()
        )
        asyncio.create_task(send_with_interval(target_ids, caption, interval, content_type, file_id, message.bot))

async def send_with_interval(target_ids, text, interval, media_type, file_id, bot):
    """Отправляет сообщения по очереди с интервалом"""
    for idx, target_id in enumerate(target_ids):
        if target_id in storage.targets:
            target_data = storage.targets[target_id]
            assigned = target_data.get("assigned_accounts", []).copy()
            
            if not assigned:
                assigned = [random.choice(list(storage.accounts.keys()))] if storage.accounts else []
            
            for acc_name in assigned:
                if acc_name in storage.accounts:
                    client = storage.accounts[acc_name]["client"]
                    await send_telegram_message(
                        client, target_data, text, acc_name,
                        media_type=media_type, file_id=file_id, bot=bot
                    )
            
            if idx < len(target_ids) - 1:
                await asyncio.sleep(interval)
