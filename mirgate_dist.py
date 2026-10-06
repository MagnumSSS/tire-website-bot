import sqlite3

conn = sqlite3.connect('data/schedule.db')
cursor = conn.cursor()

# 1. Создаем таблицу raw (если ещё нет)
cursor.execute("""
CREATE TABLE IF NOT EXISTS distance_cabinets_raw (
    subject TEXT PRIMARY KEY,
    room_number TEXT NOT NULL
)
""")

# можно вставить целую таблицу в другую
cursor.execute("""
INSERT OR IGNORE INTO distance_cabinets_raw (subject, room_number)
SELECT subject, room_number FROM distance_cabinets
""")

# удаляем данные таблицы distance_cabinets
cursor.execute("DELETE FROM distance_cabinets")


# 2. Проверяем результат
cursor.execute("SELECT COUNT(*) FROM distance_cabinets_raw")
count = cursor.fetchone()[0] # надо бы понять эту концепцию 
print(f"✅ Перенесено {count} записей в distance_cabinets_raw")

conn.commit()
conn.close()