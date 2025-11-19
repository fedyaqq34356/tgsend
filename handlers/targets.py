# handlers/targets.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import AddTarget, DeleteTarget
from keyboards.main_kb import cancel_kb, targets_menu
from database.storage import storage

router = Router()

@router.message(F.text == "➕ Добавить получателя")
async def add_target_start(message: Message, state: FSMContext):
    await state.set_state(AddTarget.choosing_type)
    await message.answer(
        "Выберите тип:\n\n"
        "1️⃣ - Пользователь (по username)\n"
        "2️⃣ - Группа/Канал (по ID)\n\n"
        "Отправьте 1 или 2:",
        reply_markup=cancel_kb()
    )

@router.message(AddTarget.choosing_type, F.text.in_(["1", "2"]))
async def process_target_type(message: Message, state: FSMContext):
    if message.text == "1":
        await state.update_data(target_type="user")
        await state.set_state(AddTarget.waiting_username)
        await message.answer("Введите username (без @):")
    else:
        await state.update_data(target_type="group")
        await state.set_state(AddTarget.waiting_chat_id)
        await message.answer("Введите ID группы/канала (с минусом если есть):")

@router.message(AddTarget.waiting_username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    target_id = f"user_{username}"
    
    if target_id in storage.targets:
        await message.answer("❌ Такой получатель уже существует!")
        return
    
    storage.targets[target_id] = {
        "type": "user",
        "username": username,
        "assigned_accounts": []
    }
    
    storage.save_targets()
    await state.clear()
    await message.answer(f"✅ Пользователь @{username} добавлен!", reply_markup=targets_menu())

@router.message(AddTarget.waiting_chat_id)
async def process_chat_id(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
        target_id = f"group_{chat_id}"
        
        if target_id in storage.targets:
            await message.answer("❌ Такая группа уже существует!")
            return
        
        storage.targets[target_id] = {
            "type": "group",
            "chat_id": chat_id,
            "assigned_accounts": []
        }
        
        storage.save_targets()
        await state.clear()
        await message.answer(f"✅ Группа {chat_id} добавлена!", reply_markup=targets_menu())
    except:
        await message.answer("❌ ID должен быть числом! Попробуйте снова:")

@router.message(F.text == "📋 Список получателей")
async def show_targets(message: Message):
    if not storage.targets:
        await message.answer("❌ Нет добавленных получателей")
        return
    
    text = "👥 <b>Список получателей:</b>\n\n"
    for i, (target_id, data) in enumerate(storage.targets.items(), 1):
        if data["type"] == "user":
            text += f"{i}. 👤 @{data['username']}\n"
        else:
            text += f"{i}. 👥 Группа {data['chat_id']}\n"
        
        if data["assigned_accounts"]:
            text += f" 🔗 Аккаунты: {', '.join(data['assigned_accounts'])}\n"
        else:
            text += " 🔗 Аккаунты: не назначены\n"
        text += "\n"
    
    await message.answer(text, parse_mode="HTML")

# === НОВОЕ: Удаление получателя ===
@router.message(F.text == "🗑 Удалить получателя")
async def delete_target_start(message: Message, state: FSMContext):
    if not storage.targets:
        await message.answer("❌ Нет получателей для удаления")
        return
    
    await state.set_state(DeleteTarget.choosing_target)
    
    text = "Выберите номер получателя для удаления:\n\n"
    target_list = list(storage.targets.items())
    for i, (tid, data) in enumerate(target_list, 1):
        if data["type"] == "user":
            text += f"{i}. 👤 @{data['username']}\n"
        else:
            text += f"{i}. 👥 Группа {data['chat_id']}\n"
    
    await message.answer(text + "\nОтправьте номер:", reply_markup=cancel_kb())

@router.message(DeleteTarget.choosing_target, F.text.regexp(r'^\d+$'))
async def process_target_deletion(message: Message, state: FSMContext):
    try:
        idx = int(message.text) - 1
        target_list = list(storage.targets.keys())
        
        if 0 <= idx < len(target_list):
            target_id = target_list[idx]
            target_data = storage.targets[target_id]
            
            # Формируем читаемое имя
            if target_data["type"] == "user":
                display_name = f"@{target_data['username']}"
            else:
                display_name = f"Группу {target_data['chat_id']}"
            
            # Удаляем получателя
            del storage.targets[target_id]
            
            # Очищаем ссылки на этого получателя в черновиках
            for draft in storage.drafts:
                if target_id in draft.get("target_ids", []):
                    draft["target_ids"].remove(target_id)
            
            # Очищаем ссылки в запланированных сообщениях
            storage.scheduled_messages = [
                msg for msg in storage.scheduled_messages 
                if msg.get("target_id") != target_id
            ]
            
            # Сохраняем все изменения
            storage.save_targets()
            storage.save_drafts()
            storage.save_scheduled()
            
            await state.clear()
            await message.answer(
                f"✅ Получатель {display_name} удалён!\n"
                f"Также очищены связанные черновики и запланированные сообщения.",
                reply_markup=targets_menu()
            )
        else:
            await message.answer("❌ Неверный номер!")
    except:
        await message.answer("❌ Ошибка ввода!")
