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

# ==================== НЕМЕДЛЕННАЯ ОТПРАВКА С КНОПКОЙ ====================
@router.message(F.text == "🔘 Сообщение с кнопкой")
async def start_button_message(message: Message, state: FSMContext):
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
async def btn_choose_targets(message: Message, state: FSMContext):
    try:
        target_list = list(storage.targets.keys())
        selected = target_list.copy() if message.text.lower() == "all" else \
            [target_list[i] for i in [int(x.strip()) - 1 for x in message.text.split(',') if x.strip().isdigit()] if 0 <= i < len(target_list)]
        if not selected:
            await message.answer("❌ Не выбрано получателей!")
            return
        await state.update_data(target_ids=selected)
        await state.set_state(MessageWithButton.waiting_content)
        await message.answer(
            "Отправьте контент (текст, фото, видео или файл с подписью).\n"
            "Форматирование (жирный, курсив, ссылки) будет сохранено!",
            reply_markup=cancel_kb()
        )
    except:
        await message.answer("❌ Ошибка выбора!")

@router.message(MessageWithButton.waiting_content, F.text | F.photo | F.video | F.document)
async def btn_process_content(message: Message, state: FSMContext):
    text = (message.html_text or message.caption_html or message.text or "").strip()
    content_type = "text"
    file_id = None

    if message.photo:
        content_type, file_id = "photo", message.photo[-1].file_id
        text = message.caption_html or ""
    elif message.video:
        content_type, file_id = "video", message.video.file_id
        text = message.caption_html or ""
    elif message.document:
        content_type, file_id = "document", message.document.file_id
        text = message.caption_html or ""

    await state.update_data(text=text, content_type=content_type, file_id=file_id)
    await state.set_state(MessageWithButton.waiting_button_text)
    await message.answer("Введите текст кнопки (например: «Подробнее», «Смотреть», «Перейти»):")

@router.message(MessageWithButton.waiting_button_text)
async def btn_button_text(message: Message, state: FSMContext):
    button_text = message.text.strip() or "Перейти по ссылке 👆"
    await state.update_data(button_text=button_text)
    await state.set_state(MessageWithButton.waiting_url)
    await message.answer("Теперь отправьте URL (ссылку), на которую будет вести кнопка:")

@router.message(MessageWithButton.waiting_url, F.text.regexp(r"^https?://"))
async def btn_send_with_button(message: Message, state: FSMContext):
    url = message.text.strip()
    data = await state.get_data()
    target_ids = data["target_ids"]
    text = data["text"]
    content_type = data["content_type"]
    file_id = data.get("file_id")
    button_text = data["button_text"]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=button_text, url=url)]])

    await message.answer("📤 Отправка сообщений с кнопкой...")

    success = 0
    for tid in target_ids:
        target = storage.targets[tid]
        accounts = target.get("assigned_accounts", []) or ([random.choice(list(storage.accounts.keys()))] if storage.accounts else [])
        for acc_name in accounts:
            client = storage.accounts[acc_name]["client"]
            sent = await send_telegram_message(
                client, target, text, acc_name,
                media_type=content_type if content_type != "text" else "text",
                file_id=file_id, bot=message.bot, reply_markup=keyboard
            )
            if sent:
                success += 1
            await asyncio.sleep(2)

    await state.clear()
    await message.answer(f"✅ Готово! Отправлено: {success}", reply_markup=main_menu())

# ==================== ПЛАНИРОВАНИЕ С КНОПКОЙ ====================
@router.message(F.text == "🔘 Запланировать с кнопкой")
async def schedule_button_start(message: Message, state: FSMContext):
    if not storage.targets:
        await message.answer("❌ Сначала добавьте получателей!", reply_markup=scheduler_menu())
        return

    text = "Выберите получателей (номера через запятую или 'all'):\n\n"
    for i, (tid, data) in enumerate(storage.targets.items(), 1):
        text += f"{i}. @{data['username']}" if data["type"] == "user" else f"{i}. Группа {data['chat_id']}\n"
    await state.set_state(ScheduleWithButton.choosing_targets)
    await message.answer(text, reply_markup=cancel_kb())

# (дальше копируем логику, только в конце сохраняем в scheduled_messages с reply_markup)
@router.message(ScheduleWithButton.choosing_targets)
async def sched_btn_targets(message: Message, state: FSMContext):
    # аналогично btn_choose_targets, но состояние ScheduleWithButton
    try:
        target_list = list(storage.targets.keys())
        selected = target_list.copy() if message.text.lower() == "all" else \
            [target_list[i] for i in [int(x.strip()) - 1 for x in message.text.split(',') if x.strip().isdigit()] if 0 <= i < len(target_list)]
        if not selected:
            await message.answer("❌ Не выбрано!")
            return
        await state.update_data(target_ids=selected)
        await state.set_state(ScheduleWithButton.waiting_content)
        await message.answer("Отправьте контент (текст/фото/видео/файл):", reply_markup=cancel_kb())
    except:
        await message.answer("❌ Ошибка!")

@router.message(ScheduleWithButton.waiting_content, F.text | F.photo | F.video | F.document)
async def sched_btn_content(message: Message, state: FSMContext):
    # аналогично btn_process_content
    text = (message.html_text or message.caption_html or message.text or "").strip()
    ctype = "text"
    fid = None
    if message.photo:
        ctype, fid = "photo", message.photo[-1].file_id
        text = message.caption_html or ""
    elif message.video:
        ctype, fid = "video", message.video.file_id
        text = message.caption_html or ""
    elif message.document:
        ctype, fid = "document", message.document.file_id
        text = message.caption_html or ""

    await state.update_data(text=text, content_type=ctype, file_id=fid)
    await state.set_state(ScheduleWithButton.waiting_button_text)
    await message.answer("Текст кнопки:")

@router.message(ScheduleWithButton.waiting_button_text)
async def sched_btn_text(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text.strip() or "Перейти")
    await state.set_state(ScheduleWithButton.waiting_url)
    await message.answer("URL кнопки:")

@router.message(ScheduleWithButton.waiting_url, F.text.regexp(r"^https?://"))
async def sched_btn_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text.strip())
    await state.set_state(ScheduleWithButton.waiting_time)
    now = datetime.now() + timedelta(hours=2)
    await message.answer(
        f"⏰ Текущее время: {now.strftime('%d.%m.%Y %H:%M')}\n\n"
        "Когда отправить?\nФормат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Или: +5м, +2ч, +1д"
    )

@router.message(ScheduleWithButton.waiting_time)
async def sched_btn_time(message: Message, state: FSMContext):
    # упрощённая обработка времени (как в scheduler.py)
    try:
        txt = message.text.strip()
        if txt.startswith('+'):
            delta = txt[1:]
            if 'д' in delta: minutes = int(delta.replace('д','')) * 1440
            elif 'ч' in delta: minutes = int(delta.replace('ч','')) * 60
            elif 'м' in delta: minutes = int(delta.replace('м',''))
            else: raise ValueError
            send_time = datetime.now() + timedelta(minutes=minutes)
        else:
            d, t = txt.split()
            date_part = d.split('.')
            time_part = t.replace('.', ':')
            user_time = datetime.strptime(f"{date_part[2]}-{date_part[1]}-{date_part[0]} {time_part}", "%Y-%m-%d %H:%M")
            send_time = user_time - timedelta(hours=2)

        data = await state.get_data()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=data["button_text"], url=data["url"])]])

        for tid in data["target_ids"]:
            storage.scheduled_messages.append({
                "time": send_time.strftime("%Y-%m-%d %H:%M:%S"),
                "target_id": tid,
                "text": data["text"],
                "content_type": data["content_type"],
                "file_id": data.get("file_id"),
                "reply_markup": keyboard.json(),  # сохраняем как dict
                "accounts": storage.targets[tid].get("assigned_accounts", [])
            })

        storage.save_scheduled()
        await state.clear()
        await message.answer(f"✅ Запланировано на {(send_time + timedelta(hours=2)).strftime('%d.%m.%Y %H:%M')}", reply_markup=scheduler_menu())
    except:
        await message.answer("❌ Неверный формат времени!")
