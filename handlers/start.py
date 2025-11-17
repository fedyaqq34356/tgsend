# handlers/start.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from keyboards.main_kb import main_menu, accounts_menu, targets_menu, drafts_menu, scheduler_menu, stats_menu, assignments_menu
from config import ADMIN_IDS

router = Router()

def check_access(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя доступ к боту"""
    if not ADMIN_IDS:  # Если список пустой - доступ всем
        return True
    return user_id in ADMIN_IDS

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    # Выводим ID пользователя для настройки ADMIN_IDS
    print(f"[INFO] Пользователь {message.from_user.id} ({message.from_user.full_name}) запустил бота")
    
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту")
        return
    
    await state.clear()
    await message.answer(
        "🤖 <b>Telegram Multi-Account Manager</b>\n\n"
        "Управляйте несколькими аккаунтами Telegram и отправляйте сообщения!\n\n"
        "Выберите раздел:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "◀️ Назад")
async def back_to_main(message: Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu())

@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=main_menu())

@router.message(F.text == "📱 Аккаунты")
async def accounts_section(message: Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту")
        return
    await message.answer("📱 <b>Управление аккаунтами</b>", reply_markup=accounts_menu(), parse_mode="HTML")

@router.message(F.text == "👥 Получатели")
async def targets_section(message: Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту")
        return
    await message.answer("👥 <b>Управление получателями</b>", reply_markup=targets_menu(), parse_mode="HTML")

@router.message(F.text == "📝 Черновики")
async def drafts_section(message: Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту")
        return
    await message.answer("📝 <b>Управление черновиками</b>", reply_markup=drafts_menu(), parse_mode="HTML")

@router.message(F.text == "⏰ Планирование")
async def scheduler_section(message: Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту")
        return
    await message.answer("⏰ <b>Планирование сообщений</b>", reply_markup=scheduler_menu(), parse_mode="HTML")

@router.message(F.text == "📊 Статистика")
async def stats_section(message: Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту")
        return
    await message.answer("📊 <b>Статистика</b>", reply_markup=stats_menu(), parse_mode="HTML")

@router.message(F.text == "🔗 Назначения")
async def assignments_section(message: Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту")
        return
    await message.answer("🔗 <b>Управление назначениями</b>", reply_markup=assignments_menu(), parse_mode="HTML")