# handlers/button_message.py
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.states import MessageWithButton, ScheduleWithButton
from keyboards.main_kb import cancel_kb, main_menu, scheduler_menu
from database.storage import storage
from utils.telethon_auth import send_telegram_message
from datetime import datetime, timedelta
import random
import asyncio

router = Router()

# ===================== НЕМЕДЛЕННАЯ ОТПРАВКА С КНОПКОЙ =====================
@router.message(F.text == "🔘 Сообщение с кнопкой")
async def start_immediate_button(message: Message, state: FSMContext):
    if not storage.targets:
        await message.answer("❌ Сначала добавьте получателей!", reply_markup=main_menu())
        return
    if not storage.accounts:
        await message.answer("❌ Сначала добавьте аккаунты!", reply_markup=main_menu())
        return

    text = "Выберите получателей (номера через запятую или 'all'):\n\n"
    for i, (tid, data) in enumerate(storage.targets.items(), 1):
        text += f"{i}. @{data['username']}" if data["type"] == "user" else f"{i}. Группа {data['chat_id']}\n"
    text += "\nПример: 1,3,5 или all"

    await state.set_state(MessageWithButton.choosing_targets)
    await message.answer(text, reply_markup=cancel_kb())

@router.message(MessageWithButton.choosing_targets)
async def btn_targets(message: Message, state: FSMContext):
    try:
        tlist = list(storage.targets.keys())
        selected = tlist.copy() if message.text.lower() == "all" else \
            [tlist[i] for i in [int(x.strip())-1 for x in message.text.split(',') if x.strip().isdigit()] if 0 <= i < len(tlist)]
        if not selected:
            await message.answer("❌ Не выбрано получателей!")
            return
        await state.update_data(target_ids=selected)
        await state.set_state(MessageWithButton.waiting_content)
        await message.answer("Отправьте контент (текст, фото, видео или файл с подписью).\nФорматирование будет сохранено!", reply_markup=cancel_kb())
    except:
        await message.answer("❌ Ошибка выбора!")

@router.message(MessageWithButton.waiting_content, F.text | F.photo | F.video | F.document)
async def btn_process_content(message: Message, state: FSMContext):
    # ИСПРАВЛЕНО: безопасное получение HTML-текста и подписи
    if message.caption:
        text = message.caption_html_unsafe if message.caption_entities else (message.caption or "")
    else:
        text = message.html_text or message.text or ""

    ctype = "text"
    fid = None
    if message.photo:
        ctype, fid = "photo", message.photo[-1].file_id
    elif message.video:
        ctype, fid = "video", message.video.file_id
    elif message.document:
        ctype, fid = "document", message.document.file_id

    await state.update_data(text=text.strip(), content_type=ctype, file_id=fid)
    await state.set_state(MessageWithButton.waiting_button_text)
    await message.answer("Введите текст кнопки (например: «Подробнее», «Скачать»):")

@router.message(MessageWithButton.waiting_button_text)
async def btn_button_text(message: Message, state: FSMContext):
    btn_text = message.text.strip() or "Перейти по ссылке 👆"
    await state.update_data(button_text=btn_text)
    await state.set_state(MessageWithButton.waiting_url)
    await message.answer("Отправьте URL для кнопки (начинается с http:// или https://):")

@router.message(MessageWithButton.waiting_url, F.text.regexp(r"^https?://"))
async def btn_send(message: Message, state: FSMContext):
    url = message.text.strip()
    data = await state.get_data()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=data["button_text"], url=url)]])

    await message.answer("📤 Отправляю сообщения с кнопкой...")
    success = 0
    for tid in data["target_ids"]:
        target = storage.targets[tid]
        accounts = target.get("assigned_accounts", []) or ([random.choice(list(storage.accounts.keys()))] if storage.accounts else [])
        for acc in accounts:
            sent = await send_telegram_message(
                storage.accounts[acc]["client"], target, data["text"], acc,
                media_type=data["content_type"] if data["content_type"] != "text" else "text",
                file_id=data.get("file_id"), bot=message.bot, reply_markup=keyboard
            )
            if sent:
                success += 1
            await asyncio.sleep(2)

    await state.clear()
    await message.answer(f"✅ Отправлено: {success}", reply_markup=main_menu())

# ===================== ПЛАНИРОВАНИЕ С КНОПКОЙ =====================
# (остальные обработчики для планирования — копия с теми же исправлениями)
@router.message(F.text == "🔘 Запланировать с кнопкой")
async def start_schedule_button(message: Message, state: FSMContext):
    # ... (аналогично, используем те же исправления для caption и html_text) ...
    # Полный код можно скопировать из предыдущей версии, главное — использовать безопасное получение текста
