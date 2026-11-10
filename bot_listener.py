# /opt/schedule/bot_listener.py
import os
import time
import sqlite3
import requests
from dotenv import load_dotenv
from send_widget import generate_widget_html

load_dotenv('/opt/schedule/monitor.env')
BOT_TOKEN = os.getenv('MONITOR_BOT_TOKEN')
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB = '/opt/schedule/data/schedule.db'
WEBAPP_URL = 'https://vibebunker.ru'  # твой сайт для web_app кнопки

# Текст кнопки, которая будет висеть внизу постоянно
WIDGET_BUTTON_TEXT = "📅 Расписание"


def get_group(user_id):
    """Достаёт группу пользователя из user_groups (или None)."""
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute(
            "SELECT group_name FROM user_groups WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(f"{API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"sendMessage err: {e}")


def send_widget(chat_id, group):
    """Генерит HTML-виджет и отправляет через sendWidget. Возвращает bool."""
    try:
        html = generate_widget_html(group)
        r = requests.post(f"{API}/sendWidget", json={
            "chat_id": chat_id,
            "html": html,
            "width": 0,
            "height": 0,
            "caption": f"📅 Расписание {group}",
        }, timeout=15)
        data = r.json()
        ok = data.get("ok", False)
        if not ok:
            print(f"sendWidget fail: {data}")
        return ok
    except Exception as e:
        print(f"sendWidget err: {e}")
        return False


def answer_callback(cb_id, text):
    try:
        requests.post(f"{API}/answerCallbackQuery", json={
            "callback_query_id": cb_id,
            "text": text
        }, timeout=10)
    except Exception as e:
        print(f"answerCallbackQuery err: {e}")


def handle_start(chat_id, user_id):
    """Обработка /start: приветствие + постоянная кнопка внизу (или web_app на сайт)."""
    group = get_group(user_id)

    if group:
        # Группа ЕСТЬ → нормальная клавиатура с «📅 Расписание»
        keyboard = {
            "keyboard": [[{"text": WIDGET_BUTTON_TEXT}]],
            "resize_keyboard": True,
            "is_persistent": True,
        }
        send_message(
            chat_id,
            f"👋 Привет! Твоя группа — {group}.\n"
            f"Жми кнопку внизу — пришлю расписание.",
            keyboard,
        )
    else:
        # Группы НЕТ → две кнопки: «Открыть сайт» (inline web_app) + «🔄 Проверить группу» (reply)
        inline_keyboard = {
            "inline_keyboard": [[
                {"text": "Открыть сайт", "web_app": {"url": WEBAPP_URL}}
            ]]
        }
        # Сначала inline с web_app на сайт
        send_message(
            chat_id,
            "Сначала открой сайт — я запомню твою группу.\n"
            "Как выберешь группу — вернись сюда и нажми 🔄 Проверить группу.",
            inline_keyboard,
        )
        # Затем reply-клавиатура с «🔄 Проверить группу» (останется внизу)
        reply_keyboard = {
            "keyboard": [[{"text": "🔄 Проверить группу"}]],
            "resize_keyboard": True,
            "is_persistent": True,
        }
        send_message(
            chat_id,
            "Когда выберешь группу на сайте — жми кнопку внизу.",
            reply_keyboard,
        )

def handle_check_group(chat_id, user_id):
    group = get_group(user_id)
    if group:
        # Группа появилась — шлём нормальную клавиатуру с «📅 Расписание»
        keyboard = {
            "keyboard": [[{"text": WIDGET_BUTTON_TEXT}]],
            "resize_keyboard": True,
            "is_persistent": True,
        }
        send_message(
            chat_id,
            f"✅ Вижу группу {group}. Жми кнопку внизу — пришлю расписание.",
            keyboard,
        )
    else:
        send_message(
            chat_id,
            "Пока не вижу группу. Открой сайт, выбери группу — и жми 🔄 снова.",
        )

def handle_widget_request(chat_id, user_id):
    """Общая логика на нажатие кнопки '📅 Расписание' и /widget."""
    group = get_group(user_id)
    if group:
        ok = send_widget(chat_id, group)
        if not ok:
            send_message(chat_id, "Не удалось отправить виджет. Попробуй ещё раз.")
    else:
        send_message(chat_id, "Сначала открой сайт, чтобы я запомнил группу.")


def handle_callback(cb):
    """Обработка нажатия на inline-кнопку '📅 Прислать расписание' (старая из истории)."""
    user_id = cb["from"]["id"]
    chat_id = cb["message"]["chat"]["id"]
    cb_id = cb["id"]

    if cb.get("data") == "send_schedule":
        group = get_group(user_id)
        if group:
            ok = send_widget(chat_id, group)
            answer_callback(cb_id, "Отправляю..." if ok else "Ошибка отправки")
        else:
            answer_callback(cb_id, "Группа не найдена. Открой сайт.")


def main():
    offset = 0
    print("bot_listener started")

    while True:
        try:
            r = requests.get(
                f"{API}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35,
            ).json()

            for upd in r.get("result", []):
                offset = upd["update_id"] + 1

                # ---- Обычные сообщения ----
                msg = upd.get("message")
                if msg:
                    text = msg.get("text", "")
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]

                    if text == "/start":
                        handle_start(chat_id, user_id)
                    elif text == "🔄 Проверить группу":
                        handle_check_group(chat_id, user_id)
                    elif text == "/widget":
                        handle_widget_request(chat_id, user_id)
                    elif text == WIDGET_BUTTON_TEXT:
                        handle_widget_request(chat_id, user_id)

                # ---- Нажатия на inline-кнопки ----
                cb = upd.get("callback_query")
                if cb:
                    handle_callback(cb)

        except Exception as e:
            print(f"err: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()