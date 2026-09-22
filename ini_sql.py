import sqlite3
def ini_db():
    # создаем и подключаемся к бд
    with sqlite3.connect('data/schedule.db') as conn:
        # создаем курсор
        cursor = conn.cursor()

        # вставляем НОВУЮ ГРУППУ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_name TEXT PRIMARY KEY,
                file_path TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                run_id INTEGER,
                group_name TEXT NOT NULL,
                pair_number INTEGER NOT NULL,
                day_of_week TEXT NOT NULL,
                subject TEXT,
                room TEXT,
                UNIQUE(group_name, day_of_week, pair_number)
            );
        """)
        # id INTEGER PRIMARY KEY AUTOINCREMENT - означает, что бд будет сама придумывать уникальный id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parser_runs ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pair_times (
                day_type TEXT NOT NULL,
                pair_number INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL
            );
        """)

        

        conn.commit()