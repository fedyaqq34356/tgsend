from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import AddAccount
from keyboards.main_kb import cancel_kb, accounts_menu
from utils.telethon_auth import start_auth, submit_code, submit_password, cancel_auth
from database.storage import storage

router = Router()

@router.message(F.text == "➕ Добавить аккаунт")
async def add_account_start(message: Message, state: FSMContext):
    await state.set_state(AddAccount.waiting_session_name)
    await message.answer(
        "Введите уникальное название для сессии аккаунта:\n"
        "(Например: my_account)",
        reply_markup=cancel_kb()
    )

@router.message(AddAccount.waiting_session_name)
async def process_session_name(message: Message, state: FSMContext):
    session_name = message.text.strip()
    if session_name in storage.accounts:
        await message.answer("❌ Аккаунт с таким именем уже существует!\nВведите другое название:")
        return
    await state.update_data(session_name=session_name)
    await state.set_state(AddAccount.waiting_api_id)
    await message.answer("Введите API ID:\n(Получить можно на https://my.telegram.org)")

@router.message(AddAccount.waiting_api_id)
async def process_api_id(message: Message, state: FSMContext):
    try:
        api_id = int(message.text.strip())
        await state.update_data(api_id=api_id)
        await state.set_state(AddAccount.waiting_api_hash)
        await message.answer("Введите API Hash:")
    except:
        await message.answer("❌ API ID должен быть числом! Попробуйте снова:")

@router.message(AddAccount.waiting_api_hash)
async def process_api_hash(message: Message, state: FSMContext):
    api_hash = message.text.strip()
    await state.update_data(api_hash=api_hash)
    await state.set_state(AddAccount.waiting_phone)
    await message.answer("Введите номер телефона (в формате +380XXXXXXXXX):")

@router.message(AddAccount.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.get_data()
    success, result = await start_auth(
        message.from_user.id,
        data["session_name"],
        data["api_id"],
        data["api_hash"],
        phone
    )
    if success:
        await state.set_state(AddAccount.waiting_code)
        await message.answer(
            f"{result}\n\n"
            "💡 <b>Для безопасности введите код по одной цифре через пробел</b>\n"
            "Пример: 6 2 3 7 8",
            parse_mode="HTML"
        )
    else:
        await state.clear()
        await message.answer(f"❌ {result}", reply_markup=accounts_menu())

@router.message(AddAccount.waiting_code)
async def process_code(message: Message, state: FSMContext):
    digits = [d.strip() for d in message.text.split() if d.strip().isdigit()]
    if len(digits) != 5:
        await message.answer(
            "❌ Код должен состоять ровно из 5 цифр, введённых через пробел!\n"
            "Пример: 6 2 3 7 8\n\nПопробуйте снова:"
        )
        return
    code = ''.join(digits)
    result_type, result_msg = await submit_code(message.from_user.id, code)
    if result_type is True:
        await state.clear()
        await message.answer(result_msg, reply_markup=accounts_menu())
    elif result_type == "2fa":
        await state.set_state(AddAccount.waiting_password)
        await message.answer(result_msg)
    elif result_type == "retry":
        await message.answer(f"{result_msg}\n\n💡 Введите новый код по одной цифре через пробел:")
    else:
        await state.clear()
        await cancel_auth(message.from_user.id)
        await message.answer(f"❌ {result_msg}", reply_markup=accounts_menu())

@router.message(AddAccount.waiting_password)
async def process_password(message: Message, state: FSMContext):
    password = message.text.strip()
    success, result = await submit_password(message.from_user.id, password)
    await state.clear()
    if success:
        await message.answer(result, reply_markup=accounts_menu())
    else:
        await cancel_auth(message.from_user.id)
        await message.answer(f"❌ {result}", reply_markup=accounts_menu())


@router.message(F.text == "📋 Список аккаунтов")
async def show_accounts(message: Message):
    if not storage.accounts:
        await message.answer("❌ Нет добавленных аккаунтов")
        return
    text = "📱 <b>Список аккаунтов:</b>\n\n"
    for i, (name, acc) in enumerate(storage.accounts.items(), 1):
        status = "🟢" if acc["client"].is_connected() else "🔴"
        phone = acc.get("phone", "нет номера")
        text += f"{i}. {status} <b>{name}</b>\n 📞 {phone}\n\n"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🗑 Удалить аккаунт")
async def delete_account_start(message: Message, state: FSMContext):
    if not storage.accounts:
        await message.answer("❌ Нет аккаунтов для удаления")
        return
    await state.set_state(AddAccount.deleting_account)
    text = "Выберите номер аккаунта для удаления:\n\n"
    acc_list = list(storage.accounts.keys())
    for i, name in enumerate(acc_list, 1):
        text += f"{i}. {name}\n"
    await message.answer(text + "\nОтправьте номер:", reply_markup=cancel_kb())

@router.message(AddAccount.deleting_account, F.text.regexp(r'^\d+$'))
async def process_account_deletion(message: Message, state: FSMContext):
    try:
        idx = int(message.text) - 1
        acc_list = list(storage.accounts.keys())
        if 0 <= idx < len(acc_list):
            name = acc_list[idx]
            if storage.accounts[name]["client"]:
                try:
                    await storage.accounts[name]["client"].disconnect()
                except:
                    pass
            for target in storage.targets.values():
                if name in target.get("assigned_accounts", []):
                    target["assigned_accounts"].remove(name)
            del storage.accounts[name]
            storage.save_accounts()
            storage.save_targets()
            await state.clear()
            await message.answer(f"✅ Аккаунт '{name}' удален!", reply_markup=accounts_menu())
        else:
            await message.answer("❌ Неверный номер!")
    except:
        await message.answer("❌ Ошибка ввода!")
