from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import ScheduleMessage, DeleteScheduled
from keyboards.main_kb import cancel_kb, scheduler_menu, content_type_kb
from database.storage import storage
from datetime import datetime, timedelta

router = Router()

# === Запланировать сообщение ===
@router.message(F.text == "➕ Запланировать")
async def schedule_start(message: Message, state: FSMContext):
    if not storage.targets:
        await message.answer("❌ Сначала добавьте получателей!")
        return
    
    text = "Выберите получателей (номера через запятую или 'all'):\n\n"
    target_list = list(storage.targets.items())
    for i, (tid, data) in enumerate(target_list, 1):
        if data["type"] == "user":
            text += f"{i}. @{data['username']}\n"
        else:
            text += f"{i}. Группа {data['chat_id']}\n"
    
    text += "\nПример: 1,3,5 или all"
    await state.set_state(ScheduleMessage.choosing_targets)
    await message.answer(text, reply_markup=cancel_kb())

@router.message(ScheduleMessage.choosing_targets)
async def process_schedule_targets(message: Message, state: FSMContext):
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
        await state.set_state(ScheduleMessage.waiting_content_type)
        await message.answer(
            f"✅ Выбрано получателей: {len(selected_targets)}\n\n"
            "Что отправить?",
            reply_markup=content_type_kb()
        )
    except:
        await message.answer("❌ Ошибка! Попробуйте снова:")

@router.message(ScheduleMessage.waiting_content_type)
async def process_schedule_content_type(message: Message, state: FSMContext):
    content_type = message.text
    
    if content_type == "💬 Текст":
        await state.update_data(content_type="text")
        await state.set_state(ScheduleMessage.waiting_text)
        await message.answer("Введите текст сообщения:", reply_markup=cancel_kb())
    elif content_type == "🖼 Фото":
        await state.update_data(content_type="photo")
        await state.set_state(ScheduleMessage.waiting_media)
        await message.answer("Отправьте фото (можно с подписью):", reply_markup=cancel_kb())
    elif content_type == "🎥 Видео":
        await state.update_data(content_type="video")
        await state.set_state(ScheduleMessage.waiting_media)
        await message.answer("Отправьте видео (можно с подписью):", reply_markup=cancel_kb())
    elif content_type == "📎 Файл":
        await state.update_data(content_type="document")
        await state.set_state(ScheduleMessage.waiting_media)
        await message.answer("Отправьте файл (можно с подписью):", reply_markup=cancel_kb())
    else:
        await message.answer("❌ Выберите тип из кнопок!")

@router.message(ScheduleMessage.waiting_text)
async def process_schedule_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(ScheduleMessage.waiting_time)
    
    now = datetime.now() + timedelta(hours=2)
    await message.answer(
        f"⏰ Ваше текущее время: {now.strftime('%d.%m.%Y %H:%M')}\n\n"
        "Когда отправить?\n\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 20.12.2025 15:30\n\n"
        "Или быстрые команды:\n"
        "• +5м - через 5 минут\n"
        "• +2ч - через 2 часа\n"
        "• +1д - через 1 день"
    )

@router.message(ScheduleMessage.waiting_media)
async def process_schedule_media(message: Message, state: FSMContext):
    data = await state.get_data()
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
    
    await state.update_data(file_id=file_id, text=caption)
    await state.set_state(ScheduleMessage.waiting_time)
    
    now = datetime.now() + timedelta(hours=2)
    await message.answer(
        f"⏰ Ваше текущее время: {now.strftime('%d.%m.%Y %H:%M')}\n\n"
        "Когда отправить?\n\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 20.12.2025 15:30\n\n"
        "Или быстрые команды:\n"
        "• +5м - через 5 минут\n"
        "• +2ч - через 2 часа\n"
        "• +1д - через 1 день"
    )

@router.message(ScheduleMessage.waiting_time)
async def process_schedule_time(message: Message, state: FSMContext):
    try:
        time_str = message.text.strip()
        
        # Обработка быстрых команд
        if time_str.startswith('+'):
            now = datetime.now()
            amount = int(''.join(filter(str.isdigit, time_str)))
            
            if 'м' in time_str or 'm' in time_str.lower():
                send_time = now + timedelta(minutes=amount)
            elif 'ч' in time_str or 'h' in time_str.lower():
                send_time = now + timedelta(hours=amount)
            elif 'д' in time_str or 'd' in time_str.lower():
                send_time = now + timedelta(days=amount)
            else:
                raise ValueError("Неизвестный формат быстрой команды")
        else:
            # Обычный ввод даты и времени
            parts = time_str.split(' ')
            if len(parts) == 2:
                date_part = parts[0]
                time_part = parts[1].replace('.', ':')
                time_str = f"{date_part} {time_part}"
            
            user_time = datetime.strptime(time_str, "%d.%m.%Y %H:%M")
            send_time = user_time - timedelta(hours=2)
        
        data = await state.get_data()
        target_ids = data["target_ids"]
        text = data.get("text", "")
        content_type = data.get("content_type", "text")
        file_id = data.get("file_id")
        
        for target_id in target_ids:
            if target_id in storage.targets:
                assigned = storage.targets[target_id].get("assigned_accounts", []).copy()
                
                msg_data = {
                    "time": send_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "target_id": target_id,
                    "text": text,
                    "accounts": assigned,
                    "content_type": content_type
                }
                
                if file_id:
                    msg_data["file_id"] = file_id
                
                storage.scheduled_messages.append(msg_data)
        
        storage.save_scheduled()
        
        user_display_time = send_time + timedelta(hours=2)
        
        await state.clear()
        await message.answer(
            f"✅ Сообщения запланированы на {user_display_time.strftime('%d.%m.%Y %H:%M')}!\n"
            f"Получателей: {len(target_ids)}",
            reply_markup=scheduler_menu()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка формата времени! Попробуйте снова.\n\nПример: 20.12.2025 15:30")

# === Показать запланированные ===
@router.message(F.text == "📋 Показать запланированные")
async def show_scheduled(message: Message):
    if not storage.scheduled_messages:
        await message.answer("❌ Нет запланированных сообщений")
        return
    
    text = "⏰ <b>Запланированные сообщения:</b>\n\n"
    for i, msg in enumerate(storage.scheduled_messages, 1):
        server_time = datetime.strptime(msg['time'], "%Y-%m-%d %H:%M:%S")
        user_time = server_time + timedelta(hours=2)
        
        target_data = storage.targets.get(msg["target_id"], {})
        name = target_data.get('username', target_data.get('chat_id', 'неизвестно'))
        if target_data.get("type") == "user":
            name = f"@{name}"
        
        content_type = msg.get("content_type", "text")
        type_emoji = {"text": "💬", "photo": "🖼", "video": "🎥", "document": "📎"}.get(content_type, "💬")
        
        text += f"{i}. {type_emoji} {user_time.strftime('%d.%m.%Y %H:%M')} → {name}\n"
        if msg.get('text'):
            text += f"   {msg['text'][:40]}...\n\n"
        else:
            text += "\n"
    
    await message.answer(text, parse_mode="HTML")

# === Удалить запланированное ===
@router.message(F.text == "🗑 Удалить запланированное")
async def delete_scheduled_start(message: Message, state: FSMContext):
    if not storage.scheduled_messages:
        await message.answer("❌ Нет запланированных сообщений")
        return
    
    text = "Выберите номер для удаления:\n\n"
    for i, msg in enumerate(storage.scheduled_messages, 1):
        server_time = datetime.strptime(msg['time'], "%Y-%m-%d %H:%M:%S")
        user_time = server_time + timedelta(hours=2)
        text += f"{i}. {user_time.strftime('%d.%m %H:%M')}\n"
    
    await state.set_state(DeleteScheduled.choosing_message)
    await message.answer(text + "\nОтправьте номер:", reply_markup=cancel_kb())

@router.message(DeleteScheduled.choosing_message, F.text.regexp(r'^\d+$'))
async def process_scheduled_deletion(message: Message, state: FSMContext):
    try:
        idx = int(message.text) - 1
        if 0 <= idx < len(storage.scheduled_messages):
            removed = storage.scheduled_messages.pop(idx)
            storage.save_scheduled()
            await state.clear()
            await message.answer("✅ Запланированное сообщение удалено!", reply_markup=scheduler_menu())
        else:
            await message.answer("❌ Неверный номер!")
    except:
        await message.answer("❌ Ошибка ввода!")
