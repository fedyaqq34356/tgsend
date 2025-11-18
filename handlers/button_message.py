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
            [tlist[i] for i in [int(x.strip()) - 1 for x in message.text.split(',') if x.strip().isdigit()] if 0 <= i < len(tlist)]
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
        await message.answer("❌ Ошибка выбора получателей!")


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
    await message.answer("Отправьте URL для кнопки (должен начинаться с http:// или https://):")


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
                storage.accounts[acc]["client"],
                target,
                data["text"],
                acc,
                media_type=data["content_type"] if data["content_type"] != "text" else "text",
                file_id=data.get("file_id"),
                bot=message.bot,
                reply_markup=keyboard
            )
            if sent:
                success += 1
            await asyncio.sleep(2)

    await state.clear()
    await message.answer(f"✅ Отправлено: {success}", reply_markup=main_menu())


# ===================== ПЛАНИРОВАНИЕ С КНОПКОЙ =====================
@router.message(F.text == "🔘 Запланировать с кнопкой")
async def start_schedule_button(message: Message, state: FSMContext):
    if not storage.targets:
        await message.answer("❌ Сначала добавьте получателей!", reply_markup=scheduler_menu())
        return

    text = "Выберите получателей (номера через запятую или 'all'):\n\n"
    for i, (tid, data) in enumerate(storage.targets.items(), 1):
        text += f"{i}. @{data['username']}" if data["type"] == "user" else f"{i}. Группа {data['chat_id']}\n"

    await state.set_state(ScheduleWithButton.choosing_targets)
    await message.answer(text, reply_markup=cancel_kb())


@router.message(ScheduleWithButton.choosing_targets)
async def sched_targets(message: Message, state: FSMContext):
    await btn_targets(message, state)  # используем ту же логику


@router.message(ScheduleWithButton.waiting_content, F.text | F.photo | F.video | F.document)
async def sched_content(message: Message, state: FSMContext):
    await btn_process_content(message, state)  # тот же код


@router.message(ScheduleWithButton.waiting_button_text)
async def sched_button_text(message: Message, state: FSMContext):
    await btn_button_text(message, state)


@router.message(ScheduleWithButton.waiting_url, F.text.regexp(r"^https?://"))
async def sched_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text.strip())
    await state.set_state(ScheduleWithButton.waiting_time)

    now = datetime.now() + timedelta(hours=2)
    await message.answer(
        f"⏰ Текущее время (ваше): {now.strftime('%d.%m.%Y %H:%M')}\n\n"
        "Когда отправить?\nФормат: ДД.ММ.ГГГГ ЧЧ:ММ\nили +5м / +2ч / +1д"
    )


@router.message(ScheduleWithButton.waiting_time)
async def sched_time(message: Message, state: FSMContext):
    try:
        txt = message.text.strip()
        if txt.startswith('+'):
            num = int(''.join(filter(str.isdigit, txt)))
            if 'д' in txt.lower():
                delta = timedelta(days=num)
            elif 'ч' in txt.lower():
                delta = timedelta(hours=num)
            else:
                delta = timedelta(minutes=num)
            send_time = datetime.now() + delta
        else:
            d, t = txt.split(maxsplit=1)
            send_time = datetime.strptime(f"{d} {t}", "%d.%m.%Y %H:%M") - timedelta(hours=2)

        data = await state.get_data()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=data["button_text"], url=data["url"])]])
        user_time = send_time + timedelta(hours=2)

        for tid in data["target_ids"]:
            storage.scheduled_messages.append({
                "time": send_time.strftime("%Y-%m-%d %H:%M:%S"),
                "target_id": tid,
                "text": data["text"],
                "content_type": data["content_type"],
                "file_id": data.get("file_id"),
                "reply_markup": keyboard.to_python(),
                "accounts": storage.targets[tid].get("assigned_accounts", [])
            })

        storage.save_scheduled()
        await state.clear()
        await message.answer(f"✅ Запланировано на {user_time.strftime('%d.%m.%Y %H:%M')}", reply_markup=scheduler_menu())

    except Exception as e:
        await message.answer("❌ Неверный формат времени! Попробуйте снова.")
