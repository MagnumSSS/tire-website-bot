import sqlite3
import pandas_parser4fn 
import parser_n1
import add_time

DAYS = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"]

# запускаем парс групп, потом по этим группам уже парс расписания. в этом парсе находится инициализация бд
parser_n1.ini_parser_groups()
# заполняем расписание
add_time.init_times()

with sqlite3.connect('data/schedule.db') as conn:
    # создаем курсор
    cursor = conn.cursor()


    # 1. Читаем все группы из БД
    cursor.execute("SELECT group_name, file_path FROM groups")
    groups = cursor.fetchall()  # Возвращает список кортежей: [('СА-371', 'raw_schedule7.html'), ...]
    
    # DEBUG
    print(f"Найдено {len(groups)} групп. Начинаем парсинг...")

    #1.1 инструкции для идеи, которая показывает, когда изменилось расписание
    cursor.execute("INSERT INTO parser_runs (start_time, status) VALUES (CURRENT_TIMESTAMP, 'running')")
    # забираем id
    run_id = cursor.lastrowid

    conn.commit()

    # 2. двойной цикл, группа > дни
    for group_name, file_path in groups:
        path = f"data/{file_path}"
        for day in DAYS:
            print(f"Парсим группу: {group_name} в {day}")
            pandas_parser4fn.parse_and_save_schedule(conn, group_name, day, path, run_id)

    # для 1.1
    # так как, run_id это переменная, то чтобы прога не искала run_id в parser_runs(ее там нет),
    # мы делаем такую конструкцию ... WHERE id = ?", (run_id,). ? - как в f строке, run_id ставится на место вопроса
    cursor.execute("UPDATE parser_runs SET end_time = CURRENT_TIMESTAMP, status = 'success' WHERE id = ?", (run_id,))

    # 3 Коммит
    conn.commit()

    # 4. Проверка результата
    cursor.execute("SELECT COUNT(*) FROM schedule")
    total = cursor.fetchone()[0]
    print(f"\n✅ Готово! Всего записей в БД: {total}")
