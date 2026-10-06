# approve_distance.py
import sqlite3

conn = sqlite3.connect('data/schedule.db')
cursor = conn.cursor()

# Показать все сырые записи
cursor.execute("SELECT * FROM distance_cabinets_raw ORDER BY subject")
for row in cursor.fetchall():
    print(f"{row[0]} → {row[1]}")

# Спросить, какие перенести
subject = ""
count = 0
while True:
    subject = input("Какой предмет перенести в verified? (или 'exit'): ")
    # проверка на несуществующие предметы
    cursor.execute("SELECT COUNT(*) FROM distance_cabinets_raw WHERE subject = ?", (subject,))
    if subject == "exit":
        print(f"✅ Перенесено {count} записей в distance_cabinets")
        break
    elif cursor.fetchone()[0] == 0:
        print(f"❌ Предмет '{subject}' не найден в raw таблице")
        continue
    elif subject != "exit":
        cursor.execute("""
            INSERT OR REPLACE INTO distance_cabinets (subject, room_number)
            SELECT subject, room_number FROM distance_cabinets_raw WHERE subject = ?
        """, (subject,))
        cursor.execute("DELETE FROM distance_cabinets_raw WHERE subject = ?", (subject,))
        conn.commit()
        print(f"✅ {subject} перенесён")
        count += 1

conn.close()