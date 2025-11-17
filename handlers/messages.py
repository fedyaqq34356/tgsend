# handlers/messages.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import SendMessage
from keyboards.main_kb import cancel_kb, main_menu
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
    
    await state.set_state(SendMessage.choosing_target)
    
    text = "Выберите получателя (отправьте номер):\n\n"
    target_list = list(storage.targets.items())
    for i, (tid, data) in enumerate(target_list, 1):
        if data["type"] == "user":
            text += f"{i}. @{data['username']}\n"
        else:
            text += f"{i}. Группа {data['chat_id']}\n"
    
    await message.answer(text, reply_markup=cancel_kb())

@router.message(SendMessage.choosing_target, F.text.regexp(r'^\d+$'))
async def process_target_choice(message: Message, state: FSMContext):
    try:
        idx = int(message.text) - 1
        target_list = list(storage.targets.keys())
        
        if 0 <= idx < len(target_list):
            target_id = target_list[idx]
            await state.update_data(target_id=target_id)
            await state.set_state(SendMessage.waiting_text)
            await message.answer("Введите текст сообщения:")
        else:
            await message.answer("❌ Неверный номер! Попробуйте снова:")
    except:
        await message.answer("❌ Ошибка! Отправьте номер:")

@router.message(SendMessage.waiting_text)
async def process_message_text(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data["target_id"]
    text = message.text
    
    target_data = storage.targets[target_id]
    assigned = target_data.get("assigned_accounts", []).copy()
    
    if not assigned:
        await message.answer("⚠️ У этого получателя нет назначенных аккаунтов. Использовать случайный?")
        assigned = [random.choice(list(storage.accounts.keys()))]
    
    await message.answer("📤 Отправка...")
    
    success_count = 0
    for acc_name in assigned:
        if acc_name in storage.accounts:
            client = storage.accounts[acc_name]["client"]
            success = await send_telegram_message(client, target_data, text, acc_name)
            if success:
                success_count += 1
                await message.answer(f"✅ Отправлено через {acc_name}")
            else:
                await message.answer(f"❌ Ошибка отправки через {acc_name}")
            await asyncio.sleep(2)
    
    await state.clear()
    await message.answer(
        f"✅ Готово! Отправлено через {success_count} аккаунт(ов)",
        reply_markup=main_menu()
    )