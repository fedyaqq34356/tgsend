# handlers/stats.py
from aiogram import Router, F
from aiogram.types import Message
from database.storage import storage

router = Router()

@router.message(F.text == "📊 Общая статистика")
async def show_general_stats(message: Message):
    text = "📊 <b>Общая статистика:</b>\n\n"
    text += f"Всего отправлено: {storage.stats.get('sent', 0)}\n"
    text += f"Последняя отправка: {storage.stats.get('last_send', 'никогда')}"
    
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
            text += f" Последнее: {last['time'][:16]}\n"
        text += "\n"
    
    await message.answer(text, parse_mode="HTML")