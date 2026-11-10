import requests
import time
import os
import sqlite3
from dotenv import load_dotenv
from send_widget import generate_widget_html

load_dotenv('/opt/schedule/monitor.env')
BOT_TOKEN = os.getenv('MONITOR_BOT_TOKEN')
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_PATH = '/opt/schedule/data/schedule.db'

def get_user_group(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT group_name FROM user_groups WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload)

def send_widget(chat_id, group):
    html = generate_widget_html(group)
    resp = requests.post(f"{API_URL}/sendWidget", json={
        "chat_id": chat_id,
        "html": html,
        "width": 0, "height": 0,
        "caption": f"📅 Расписание {group}"
    })
    return resp.json().get("ok", False)

def main():
    offset = 0
    while True:
        try:
            updates = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35).json()
            for upd in updates.get("result", []):
                offset = upd["update_id"] + 1
                
                # Обработка обычных сообщений (команда /start)
                msg = upd.get("message")
                if msg:
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    
                    if text == "/start":
                        group = get_user_group(user_id)
                        if group:
                            # Группа уже известна — сразу показываем кнопку
                            keyboard = {
                                "inline_keyboard": [[
                                    {"text": "📅 Прислать расписание", "callback_data": "send_schedule"}
                                ]]
                            }
                            send_message(chat_id, f"Твоя группа: {group}. Нажми кнопку, чтобы получить расписание.", keyboard)
                        else:
                            # Группы нет — просим открыть сайт
                            send_message(chat_id, "Сначала открой расписание на сайте, чтобы я запомнил твою группу. Нажми /app или открой https://vibebunker.ru")
                
                # Обработка нажатий на inline-кнопки
                cb = upd.get("callback_query")
                if cb:
                    user_id = cb["from"]["id"]
                    chat_id = cb["message"]["chat"]["id"]
                    callback_id = cb["id"]
                    
                    if cb["data"] == "send_schedule":
                        group = get_user_group(user_id)
                        if group:
                            ok = send_widget(chat_id, group)
                            # Обязательно отвечаем на callback, иначе кнопка будет "крутиться"
                            requests.post(f"{API_URL}/answerCallbackQuery", json={
                                "callback_query_id": callback_id,
                                "text": "Отправляю..." if ok else "Ошибка"
                            })
                        else:
                            requests.post(f"{API_URL}/answerCallbackQuery", json={
                                "callback_query_id": callback_id,
                                "text": "Группа не найдена. Открой сайт."
                            })
        except Exception as e:
            print(f"Ошибка: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()