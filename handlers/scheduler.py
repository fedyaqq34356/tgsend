from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import ScheduleMessage, DeleteScheduled
from keyboards.main_kb import cancel_kb, scheduler_menu
from database.storage import storage
from datetime import datetime, timedelta

router = Router()

# === Запланировать сообщение ===
@router.message(F.text == "➕ Запланировать")
async def schedule_start(message: Message, state: FSMContext):
    if not storage.targets:
        await message.answer("❌ Сначала добавьте получателей!")
        return
    
    text = "Выберите получателя:\n\n"
    target_list = list(storage.targets.items())
    for i, (tid, data) in enumerate(target_list, 1):
        if data["type"] == "user":
            text += f"{i}. @{data['username']}\n"
        else:
            text += f"{i}. Группа {data['chat_id']}\n"
    
    await state.set_state(ScheduleMessage.choosing_target)
    await message.answer(text, reply_markup=cancel_kb())

@router.message(ScheduleMessage.choosing_target, F.text.regexp(r'^\d+$'))
async def process_schedule_target(message: Message, state: FSMContext):
    try:
        idx = int(message.text) - 1
        target_list = list(storage.targets.keys())
        if 0 <= idx < len(target_list):
            target_id = target_list[idx]
            await state.update_data(target_id=target_id)
            await state.set_state(ScheduleMessage.waiting_text)
            await message.answer("Введите текст сообщения:")
        else:
            await message.answer("❌ Неверный номер!")
    except:
        await message.answer("❌ Введите номер!")

@router.message(ScheduleMessage.waiting_text)
async def process_schedule_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(ScheduleMessage.waiting_time)
    
    # Показываем серверное время с поправкой +2 часа для пользователя
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
            
            # Парсим введенное время (это время пользователя с его часовым поясом)
            user_time = datetime.strptime(time_str, "%d.%m.%Y %H:%M")
            
            # Вычитаем 2 часа для серверного времени
            send_time = user_time - timedelta(hours=2)
        
        data = await state.get_data()
        target_id = data["target_id"]
        text = data["text"]
        
        assigned = storage.targets[target_id].get("assigned_accounts", []).copy()
        
        storage.scheduled_messages.append({
            "time": send_time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_id": target_id,
            "text": text,
            "accounts": assigned
        })
        
        storage.save_scheduled()
        
        # Показываем пользователю время с его поправкой
        user_display_time = send_time + timedelta(hours=2)
        
        await state.clear()
        await message.answer(
            f"✅ Сообщение запланировано на {user_display_time.strftime('%d.%m.%Y %H:%M')}!",
            reply_markup=scheduler_menu()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка формата времени!\n{e}")

# === Показать запланированные ===
@router.message(F.text == "📋 Показать запланированные")
async def show_scheduled(message: Message):
    if not storage.scheduled_messages:
        await message.answer("❌ Нет запланированных сообщений")
        return
    
    text = "⏰ <b>Запланированные сообщения:</b>\n\n"
    for i, msg in enumerate(storage.scheduled_messages, 1):
        # Парсим серверное время и добавляем 2 часа для отображения
        server_time = datetime.strptime(msg['time'], "%Y-%m-%d %H:%M:%S")
        user_time = server_time + timedelta(hours=2)
        
        target_data = storage.targets.get(msg["target_id"], {})
        name = target_data.get('username', target_data.get('chat_id', 'неизвестно'))
        if target_data.get("type") == "user":
            name = f"@{name}"
        
        text += f"{i}. {user_time.strftime('%d.%m.%Y %H:%M')} → {name}\n"
        text += f"   {msg['text'][:40]}...\n\n"
    
    await message.answer(text, parse_mode="HTML")

# === Удалить запланированное (С ОТДЕЛЬНЫМ СОСТОЯНИЕМ!) ===
@router.message(F.text == "🗑 Удалить запланированное")
async def delete_scheduled_start(message: Message, state: FSMContext):
    if not storage.scheduled_messages:
        await message.answer("❌ Нет запланированных сообщений")
        return
    
    text = "Выберите номер для удаления:\n\n"
    for i, msg in enumerate(storage.scheduled_messages, 1):
        # Показываем время с поправкой
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
