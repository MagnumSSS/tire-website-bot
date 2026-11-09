import telebot
import requests
import os
import sqlite3
from dotenv import load_dotenv
from send_widget import generate_widget_html

# Загружаем токен из твоего monitor.env
load_dotenv('/opt/schedule/monitor.env')
BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None) # parse_mode=None важен для виджетов!

@bot.message_handler(commands=['start', 'schedule'])
def send_schedule_widget(message):
    user_id = message.from_user.id
    
    # Вариант 1: Хардкод группы для теста
    group = "СА-371" 
    
    # Вариант 2 (раскомментируй, если хочешь брать из БД):
    # conn = sqlite3.connect('data/schedule.db')
    # conn.row_factory = sqlite3.Row
    # row = conn.cursor().execute("SELECT group_name FROM user_groups WHERE user_id = ?", (user_id,)).fetchone()
    # conn.close()
    # if not row:
    #     bot.send_message(user_id, "Сначала выбери группу на сайте vibebunker.ru !")
    #     return
    # group = row["group_name"]

    # Генерируем HTML
    html = generate_widget_html(group)
    
    # Отправляем через прямой запрос к API (гарантированно работает с Bot API 10.4)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendWidget"
    payload = {
        "chat_id": user_id,
        "html": html,
        "width": 0,
        "height": 0,
        "caption": f"📅 Твое расписание ({group})"
    }
    
    response = requests.post(url, json=payload)
    if response.json().get('ok'):
        bot.send_message(user_id, "✅ Виджет отправлен! (Проверь чат)")
    else:
        bot.send_message(user_id, f"❌ Ошибка отправки виджета. Убедись, что ты пишешь боту в личные сообщения, а не в группу.\nДетали: {response.text}")

print("🤖 Микро-бот запущен и слушает команды /start и /schedule...")
bot.polling(none_stop=True)