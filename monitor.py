import sys
import requests

# прописываем пути 
ENV_FILE = "/opt/schedule/monitor.env" # этот явный путь пока пусть будет, потом сменим на константу из файлы
STATE_FILE = "/opt/schedule/data/monitor_state"

# здесь пропишем еще 
HEALTH_URL = "https://vibebunker.ru/api/health"


def load_env(path):
    conf = {}
    with open(path) as f:
        # проходимся по строкам в файле
        for line in f:
            # обрезаем пробелы
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # partition("=") — расщепить строку на «ключ, разделитель, значение» 
            # по первому знаку равенства
            key, _, value = line.partition("=")
            conf[key.strip()] = value.strip()
    # возвращаем словарь
    return conf

# отправка соо пользователю
#  HTTPS-запрос к Bot API;
# sendMessage — метод отправки текста в чат;
# json= — тело запроса как JSON;
def send_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)


# функция здоровья
# любая аномалия (сеть отвалилась, таймаут, не-200, кривой JSON) трактуется как «лежит».
def check_health():
    try:
        # получаем ответ по запросу 
        r = requests.get(HEALTH_URL, timeout=10)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False

# функция прочитывания логов
def read_state():
    try:
        with open(STATE_FILE) as f:
            return f.read().strip() # возвращаем прочитанное из файла
    except FileNotFoundError:
        return "unknown" # если файла нет, а в первый раз его и не будет

# функция записи логов/состояния
def write_state(state):
    with open(STATE_FILE, "w") as f:
        f.write(state)

def main():
    # получаем словарь
    conf = load_env(ENV_FILE)
    # такой способ получить значение от ключей
    token, chat_id = conf["MONITOR_BOT_TOKEN"], conf["MONITOR_CHAT_ID"]

    # как в СИ, проверяем колво аргументов и сам аргумент
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_message(token, chat_id, "моник на связи: писать умею йоу")
        print("test_sent")
        return 

    # проверяем здоровье
    ok = check_health()
    state = "up" if ok else "down"

    # проверяем реальные состояния
    prev = read_state()

    if state != prev:
        if state == "down":
            send_message(token, chat_id, "SCHEDULE API спит бля")
        else:
            send_message(token, chat_id, "SCHEDULE API на ногах")
        write_state(state)

    print(f"health={state} prev={prev}")

main()