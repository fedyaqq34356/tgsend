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
        await state.set_state(SendMessage.waiting_content_type)
        await message.answer(
            f"✅ Выбрано получателей: {len(selected_targets)}\n\n"
            "Что отправить?",
            reply_markup=content_type_kb()
        )
    except:
        await message.answer("❌ Ошибка! Попробуйте снова:")

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

@router.message(SendMessage.waiting_text)
async def process_message_text(message: Message, state: FSMContext):
    data = await state.get_data()
    target_ids = data["target_ids"]
    
    # Используем обычный текст (без форматирования, кроме ссылок)
    text = message.text
    
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
    
    await state.clear()
    await message.answer(
        f"✅ Готово! Отправлено: {success_count}",
        reply_markup=main_menu()
    )

@router.message(SendMessage.waiting_media)
async def process_message_media(message: Message, state: FSMContext):
    data = await state.get_data()
    target_ids = data["target_ids"]
    content_type = data["content_type"]
    
    # Извлекаем подпись с HTML-форматированием
    if message.caption_html:
        caption = message.caption_html  # Сохраняет форматирование!
    else:
        caption = message.caption or ""
    
    # Получаем file_id медиа
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
    
    await state.update_data(file_id=file_id, caption=caption)
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
    
    await state.clear()
    await message.answer(
        f"✅ Готово! Отправлено: {success_count}",
        reply_markup=main_menu()
    )
