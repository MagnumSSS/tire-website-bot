import sqlite3
import pandas_parser4fn 
import parser_n1
import add_time

DAYS = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"]

parser_n1.ini_parser_groups()
add_time.init_times()

with sqlite3.connect('data/schedule.db') as conn:
    cursor = conn.cursor()

    # 1. Сохраняем ТЕКУЩЕЕ расписание в снапшот (пока оно ещё есть!)
    cursor.execute("SELECT COUNT(*) FROM schedule")
    old_count = cursor.fetchone()[0]
    
    if old_count > 0:
        cursor.execute("DELETE FROM schedule_snapshot")
        cursor.execute("""
            INSERT INTO schedule_snapshot 
            SELECT group_name, pair_number, day_of_week, subject, room 
            FROM schedule
        """)
        conn.commit()
        print(f"✅ Сохранено {old_count} записей в снапшот")
    else:
        print("⚠️  Старое расписание пустое — снапшот не создан")

    # 2. Читаем группы
    cursor.execute("SELECT group_name, file_path FROM groups")
    groups = cursor.fetchall()
    print(f"Найдено {len(groups)} групп. Начинаем парсинг...")

    # 3. Запись о запуске
    cursor.execute("INSERT INTO parser_runs (start_time, status) VALUES (CURRENT_TIMESTAMP, 'running')")
    run_id = cursor.lastrowid
    conn.commit()

    # 4. Очищаем schedule для новых данных
    cursor.execute("DELETE FROM schedule")
    conn.commit()

    # 5. Парсим НОВОЕ расписание прямо в schedule
    try:
        for group_name, file_path in groups:
            path = f"data/{file_path}"
            for day in DAYS:
                print(f"Парсим группу: {group_name} в {day}")
                pandas_parser4fn.parse_and_save_schedule(conn, group_name, day, path, run_id, table_name="schedule")
        
        # 6. Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM schedule")
        new_count = cursor.fetchone()[0]
        
        if new_count == 0:
            print("❌ ОШИБКА: Расписание пустое! Откатываемся к снапшоту...")
            cursor.execute("""
                INSERT INTO schedule 
                SELECT group_name, pair_number, day_of_week, subject, room 
                FROM schedule_snapshot
            """)
            conn.commit()
            cursor.execute("UPDATE parser_runs SET end_time = CURRENT_TIMESTAMP, status = 'error' WHERE id = ?", (run_id,))
        else:
            print(f"\n✅ Готово! Всего записей в БД: {new_count}")
            cursor.execute("UPDATE parser_runs SET end_time = CURRENT_TIMESTAMP, status = 'success' WHERE id = ?", (run_id,))
        
        conn.commit()

    except Exception as e:
        print(f"\n❌ Ошибка парсинга: {e}")
        print("Откатываемся к снапшоту...")
        cursor.execute("""
            INSERT INTO schedule 
            SELECT group_name, pair_number, day_of_week, subject, room 
            FROM schedule_snapshot
        """)
        conn.commit()
        cursor.execute("UPDATE parser_runs SET end_time = CURRENT_TIMESTAMP, status = 'error' WHERE id = ?", (run_id,))
        conn.commit()