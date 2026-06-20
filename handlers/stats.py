# handlers/stats.py
from aiogram import Router, F
from aiogram.types import Message
from database.storage import storage
import html

router = Router()

def escape_html(text):
    """Экранирует HTML-символы для безопасного отображения"""
    if not text:
        return ""
    return html.escape(str(text))

@router.message(F.text == "📊 Общая статистика")
async def show_general_stats(message: Message):
    text = "📊 <b>Общая статистика:</b>\n\n"
    text += f"Всего отправлено: {storage.stats.get('sent', 0)}\n"
    text += f"Последняя отправка: {storage.stats.get('last_send', 'никогда')}\n\n"
    
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
        text += f"👤 Аккаунт: {escape_html(latest_acc)}\n"
        text += f"📍 Кому: {escape_html(latest_msg['target'])}\n"
        text += f"💬 Текст: {escape_html(latest_msg['text'])}\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📱 Статистика по аккаунтам")
async def show_account_stats(message: Message):
    if not storage.account_stats:
        await message.answer("❌ Нет статистики")
        return
    
    text = "📱 <b>Статистика по аккаунтам:</b>\n\n"
    for name, data in storage.account_stats.items():
        text += f"<b>{escape_html(name)}</b>: {data['sent']} сообщений\n"
        
        if data.get('history'):
            history = data['history'][-10:]
            text += f"\n📋 <b>Последние {len(history)} действий:</b>\n"
            for i, msg in enumerate(reversed(history), 1):
                text += f"{i}. ⏰ {msg['time']}\n"
                text += f"   📍 {escape_html(msg['target'])}\n"
                text += f"   💬 {escape_html(msg['text'])}\n\n"
        text += "─" * 30 + "\n\n"
    
    await message.answer(text, parse_mode="HTML")
