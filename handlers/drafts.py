from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import CreateDraft, ConfigureDraft, SendDraft, DeleteDraft
from keyboards.main_kb import cancel_kb, drafts_menu, main_menu
from database.storage import storage
from utils.telethon_auth import send_telegram_message
import random
import asyncio

router = Router()

# === Создать черновик ===
@router.message(F.text == "➕ Создать черновик")
async def create_draft_start(message: Message, state: FSMContext):
    await state.set_state(CreateDraft.waiting_text)
    await message.answer("Введите текст черновика:", reply_markup=cancel_kb())

@router.message(CreateDraft.waiting_text)
async def process_draft_text(message: Message, state: FSMContext):
    draft = {
        "id": len(storage.drafts) + 1,
        "text": message.text,
        "target_ids": [],
        "accounts": []
    }
    storage.drafts.append(draft)
    storage.save_drafts()
    await state.clear()
    await message.answer(f"✅ Черновик #{draft['id']} создан!", reply_markup=drafts_menu())

# === Список черновиков ===
@router.message(F.text == "📋 Список черновиков")
async def show_drafts(message: Message):
    if not storage.drafts:
        await message.answer("❌ Нет черновиков")
        return
    
    text = "📝 <b>Черновики:</b>\n\n"
    for draft in storage.drafts:
        text += f"#{draft['id']}: {draft['text'][:50]}...\n"
        text += f"Получатели: {len(draft['target_ids'])} | Аккаунты: {len(draft['accounts'])}\n\n"
    
    await message.answer(text, parse_mode="HTML")

# === Настроить черновик ===
@router.message(F.text == "⚙️ Настроить черновик")
async def configure_draft_start(message: Message, state: FSMContext):
    if not storage.drafts:
        await message.answer("❌ Нет черновиков")
        return
    
    text = "Выберите черновик для настройки:\n\n"
    for draft in storage.drafts:
        text += f"{draft['id']}. {draft['text'][:40]}...\n"
    
    await state.set_state(ConfigureDraft.choosing_draft)
    await message.answer(text, reply_markup=cancel_kb())

@router.message(ConfigureDraft.choosing_draft, F.text.regexp(r'^\d+$'))
async def process_draft_choice(message: Message, state: FSMContext):
    try:
        draft_id = int(message.text)
        draft = next((d for d in storage.drafts if d["id"] == draft_id), None)
        if not draft:
            await message.answer("❌ Черновик не найден!")
            return
        
        await state.update_data(draft_id=draft_id)
        await state.set_state(ConfigureDraft.choosing_action)
        await message.answer(
            "Что настроить?\n\n1️⃣ Получатели\n2️⃣ Аккаунты\n\nОтправьте 1 или 2:",
            reply_markup=cancel_kb()
        )
    except:
        await message.answer("❌ Введите номер черновика!")

@router.message(ConfigureDraft.choosing_action, F.text.in_(["1", "2"]))
async def process_config_action(message: Message, state: FSMContext):
    data = await state.get_data()
    draft_id = data["draft_id"]
    draft = next((d for d in storage.drafts if d["id"] == draft_id), None)

    if message.text == "1":
        text = "Выберите получателей (номера через запятую или 'all'):\n\n"
        for i, tid in enumerate(storage.targets.keys(), 1):
            target_data = storage.targets[tid]
            name = target_data.get('username', target_data.get('chat_id'))
            text += f"{i}. {name}\n"
        
        await state.update_data(config_type="targets")
        await state.set_state(ConfigureDraft.selecting_targets)
        await message.answer(text)
    
    else:
        text = "Выберите аккаунты (номера через запятую или 'all'):\n\n"
        for i, name in enumerate(storage.accounts.keys(), 1):
            text += f"{i}. {name}\n"
        
        await state.update_data(config_type="accounts")
        await state.set_state(ConfigureDraft.selecting_accounts)
        await message.answer(text)

@router.message(ConfigureDraft.selecting_targets)
async def process_targets_selection(message: Message, state: FSMContext):
    data = await state.get_data()
    draft_id = data["draft_id"]
    draft = next((d for d in storage.drafts if d["id"] == draft_id), None)
    
    target_list = list(storage.targets.keys())
    
    if message.text.lower() == "all":
        draft["target_ids"] = target_list.copy()
    else:
        try:
            indices = [int(x.strip()) - 1 for x in message.text.split(',') if x.strip().isdigit()]
            draft["target_ids"] = [target_list[i] for i in indices if 0 <= i < len(target_list)]
        except:
            await message.answer("❌ Неверный ввод! Попробуйте снова:")
            return
    
    storage.save_drafts()
    await state.clear()
    await message.answer(f"✅ Получатели настроены ({len(draft['target_ids'])})", reply_markup=drafts_menu())

@router.message(ConfigureDraft.selecting_accounts)
async def process_accounts_selection(message: Message, state: FSMContext):
    data = await state.get_data()
    draft_id = data["draft_id"]
    draft = next((d for d in storage.drafts if d["id"] == draft_id), None)
    
    acc_list = list(storage.accounts.keys())
    
    if message.text.lower() == "all":
        draft["accounts"] = acc_list.copy()
    else:
        try:
            indices = [int(x.strip()) - 1 for x in message.text.split(',') if x.strip().isdigit()]
            draft["accounts"] = [acc_list[i] for i in indices if 0 <= i < len(acc_list)]
        except:
            await message.answer("❌ Неверный ввод! Попробуйте снова:")
            return
    
    storage.save_drafts()
    await state.clear()
    await message.answer(f"✅ Аккаунты настроены ({len(draft['accounts'])})", reply_markup=drafts_menu())

# === Отправить черновик ===
@router.message(F.text == "📤 Отправить черновик")
async def send_draft_start(message: Message, state: FSMContext):
    if not storage.drafts:
        await message.answer("❌ Нет черновиков")
        return
    
    text = "Выберите черновик для отправки:\n\n"
    for draft in storage.drafts:
        text += f"{draft['id']}. {draft['text'][:40]}...\n"
    
    await state.set_state(SendDraft.choosing_draft)
    await message.answer(text, reply_markup=cancel_kb())

@router.message(SendDraft.choosing_draft, F.text.regexp(r'^\d+$'))
async def process_draft_send(message: Message, state: FSMContext):
    try:
        draft_id = int(message.text)
        draft = next((d for d in storage.drafts if d["id"] == draft_id), None)
        if not draft:
            await message.answer("❌ Черновик не найден!")
            return
        
        if not draft["target_ids"]:
            await state.clear()
            await message.answer("❌ У черновика не настроены получатели!", reply_markup=drafts_menu())
            return
        
        await message.answer("📤 Отправка черновика...")
        
        total_sent = 0
        for target_id in draft["target_ids"]:
            if target_id in storage.targets:
                target_data = storage.targets[target_id]
                assigned = draft["accounts"] or target_data.get("assigned_accounts", [])
                if not assigned:
                    assigned = [random.choice(list(storage.accounts.keys()))] if storage.accounts else []
                
                for acc_name in assigned:
                    if acc_name in storage.accounts:
                        client = storage.accounts[acc_name]["client"]
                        success = await send_telegram_message(client, target_data, draft["text"], acc_name)
                        if success:
                            total_sent += 1
                        await asyncio.sleep(2)
        
        await state.clear()
        await message.answer(f"✅ Черновик отправлен! Успешно: {total_sent}", reply_markup=drafts_menu())
    except:
        await message.answer("❌ Ошибка отправки!")

# === Удалить черновик (С ОТДЕЛЬНЫМ СОСТОЯНИЕМ!) ===
@router.message(F.text == "🗑 Удалить черновик")
async def delete_draft_start(message: Message, state: FSMContext):
    if not storage.drafts:
        await message.answer("❌ Нет черновиков")
        return
    
    text = "Выберите черновик для удаления:\n\n"
    for draft in storage.drafts:
        text += f"{draft['id']}. {draft['text'][:40]}...\n"
    
    await state.set_state(DeleteDraft.choosing_draft)
    await message.answer(text + "\nОтправьте номер черновика:", reply_markup=cancel_kb())

@router.message(DeleteDraft.choosing_draft, F.text.regexp(r'^\d+$'))
async def process_delete_draft(message: Message, state: FSMContext):
    try:
        draft_id = int(message.text)
        draft = next((d for d in storage.drafts if d["id"] == draft_id), None)
        if draft:
            storage.drafts.remove(draft)
            storage.save_drafts()
            await state.clear()
            await message.answer(f"✅ Черновик #{draft_id} удалён!", reply_markup=drafts_menu())
        else:
            await message.answer("❌ Черновик не найден")
    except:
        await message.answer("❌ Ошибка ввода!")
