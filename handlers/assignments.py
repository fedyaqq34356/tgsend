# handlers/assignments.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import AssignAccount, RemoveAssignment
from keyboards.main_kb import cancel_kb, assignments_menu
from database.storage import storage

router = Router()

@router.message(F.text == "🔗 Назначить аккаунт")
async def assign_account_start(message: Message, state: FSMContext):
    if not storage.targets or not storage.accounts:
        await message.answer("❌ Сначала добавьте аккаунты и получателей!")
        return
    
    text = "Выберите получателя:\n\n"
    target_list = list(storage.targets.items())
    for i, (tid, data) in enumerate(target_list, 1):
        if data["type"] == "user":
            text += f"{i}. @{data['username']}\n"
        else:
            text += f"{i}. Группа {data['chat_id']}\n"
    
    await state.set_state(AssignAccount.choosing_target)
    await message.answer(text, reply_markup=cancel_kb())

@router.message(AssignAccount.choosing_target, F.text.regexp(r'^\d+$'))
async def process_assign_target(message: Message, state: FSMContext):
    try:
        idx = int(message.text) - 1
        target_list = list(storage.targets.keys())
        
        if 0 <= idx < len(target_list):
            target_id = target_list[idx]
            await state.update_data(target_id=target_id)
            await state.set_state(AssignAccount.choosing_account)
            
            text = "Выберите аккаунт:\n\n"
            acc_list = list(storage.accounts.keys())
            for i, name in enumerate(acc_list, 1):
                text += f"{i}. {name}\n"
            
            await message.answer(text)
    except:
        await message.answer("❌ Ошибка!")

@router.message(AssignAccount.choosing_account, F.text.regexp(r'^\d+$'))
async def process_assign_account(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        target_id = data["target_id"]
        
        idx = int(message.text) - 1
        acc_list = list(storage.accounts.keys())
        
        if 0 <= idx < len(acc_list):
            acc_name = acc_list[idx]
            
            if acc_name not in storage.targets[target_id]["assigned_accounts"]:
                storage.targets[target_id]["assigned_accounts"].append(acc_name)
                storage.save_targets()
                await message.answer(
                    f"✅ Аккаунт '{acc_name}' назначен!",
                    reply_markup=assignments_menu()
                )
            else:
                await message.answer("⚠️ Этот аккаунт уже назначен!", reply_markup=assignments_menu())
            
            await state.clear()
    except:
        await message.answer("❌ Ошибка!")

@router.message(F.text == "❌ Удалить назначение")
async def remove_assignment_start(message: Message, state: FSMContext):
    if not storage.targets:
        await message.answer("❌ Нет получателей!")
        return
    
    text = "Выберите получателя:\n\n"
    target_list = list(storage.targets.items())
    for i, (tid, data) in enumerate(target_list, 1):
        if data["type"] == "user":
            text += f"{i}. @{data['username']}"
        else:
            text += f"{i}. Группа {data['chat_id']}"
        
        if data["assigned_accounts"]:
            text += f" ({len(data['assigned_accounts'])})\n"
        else:
            text += " (нет назначений)\n"
    
    await state.set_state(RemoveAssignment.choosing_target)
    await message.answer(text, reply_markup=cancel_kb())

@router.message(RemoveAssignment.choosing_target, F.text.regexp(r'^\d+$'))
async def process_remove_target(message: Message, state: FSMContext):
    try:
        idx = int(message.text) - 1
        target_list = list(storage.targets.keys())
        
        if 0 <= idx < len(target_list):
            target_id = target_list[idx]
            assigned = storage.targets[target_id]["assigned_accounts"]
            
            if not assigned:
                await state.clear()
                await message.answer("❌ Нет назначений!", reply_markup=assignments_menu())
                return
            
            await state.update_data(target_id=target_id)
            await state.set_state(RemoveAssignment.choosing_account)
            
            text = "Выберите аккаунт для удаления:\n\n"
            for i, name in enumerate(assigned, 1):
                text += f"{i}. {name}\n"
            
            await message.answer(text)
    except:
        await message.answer("❌ Ошибка!")

@router.message(RemoveAssignment.choosing_account, F.text.regexp(r'^\d+$'))
async def process_remove_account(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        target_id = data["target_id"]
        
        idx = int(message.text) - 1
        assigned = storage.targets[target_id]["assigned_accounts"]
        
        if 0 <= idx < len(assigned):
            removed = assigned.pop(idx)
            storage.save_targets()
            await message.answer(
                f"✅ Аккаунт '{removed}' удален из назначений!",
                reply_markup=assignments_menu()
            )
            await state.clear()
    except:
        await message.answer("❌ Ошибка!")