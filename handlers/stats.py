# handlers/stats.py
from aiogram import Router, F
from aiogram.types import Message
from database.storage import storage

router = Router()

@router.message(F.text == "📊 Общая статистика")
async def show_general_stats(message: Message):
    text = "📊 <b>Общая статистика:</b>\n\n"
    text += f"Всего отправлено: {storage.stats.get('sent', 0)}\n"
    text += f"Последняя отправка: {storage.stats.get('last_send', 'никогда')}\n\n"
    
    # Показываем последнее сообщение из любого аккаунта
    latest_time = None
    latest_acc = None
    latest_msg = None
    
    for acc_name, acc_data in storage.account_stats.items():
        if acc_data.get('history'):
            last_msg = acc_data['history'][-1]
            msg_time = last_msg['time']
            if not latest_time or msg_time > latest_time:
                latest_time = msg_time
                latest_acc = acc_name
                latest_msg = last_msg
    
    if latest_msg:
        text += "📨 <b>Последнее сообщение:</b>\n"
        text += f"⏰ Время: {latest_msg['time']}\n"
        text += f"👤 Аккаунт: {latest_acc}\n"
        text += f"📍 Кому: {latest_msg['target']}\n"
        text += f"💬 Текст: {latest_msg['text']}\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📱 Статистика по аккаунтам")
async def show_account_stats(message: Message):
    if not storage.account_stats:
        await message.answer("❌ Нет статистики")
        return
    
    text = "📱 <b>Статистика по аккаунтам:</b>\n\n"
    for name, data in storage.account_stats.items():
        text += f"<b>{name}</b>: {data['sent']} сообщений\n"
        if data.get('history'):
            last = data['history'][-1]
            text += f"⏰ {last['time']}\n"
            text += f"📍 {last['target']}\n"
            text += f"💬 {last['text']}\n"
        text += "\n"
    
    await message.answer(text, parse_mode="HTML")
