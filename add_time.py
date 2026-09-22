import sqlite3
def init_times():
    with sqlite3.connect('data/schedule.db') as conn:
        cursor = conn.cursor()

            # Данные для обычных дней (ВТ-ПТ)
        weekday_times = [
            ("weekday", 1, "08:30", "09:15"),
            ("weekday", 1, "09:20", "10:05"),

            ("weekday", 2, "10:20", "11:05"),
            ("weekday", 2, "11:10", "11:55"),

            ("weekday", 3, "12:25", "13:10"),
            ("weekday", 3, "13:15", "14:00"),

            ("weekday", 4, "14:30", "15:15"),
            ("weekday", 4, "15:20", "16:05"),

            ("weekday", 5, "16:15", "17:00"),
            ("weekday", 5, "17:05", "17:50"),

            ("weekday", 6, "18:00", "18:45"),
            ("weekday", 6, "18:50", "19:35")
        ]

        monday_times = [
            ("monday", 0, "08:30", "09:15"),

            ("monday", 1, "09:20", "10:05"),
            ("monday", 1, "10:10", "10:55"),

            ("monday", 2, "11:15", "12:00"),
            ("monday", 2, "12:05", "12:50"),

            ("monday", 3, "13:20", "14:05"),
            ("monday", 3, "14:10", "14:55"),

            ("monday", 4, "15:15", "16:00"),
            ("monday", 4, "16:05", "16:50"),

            ("monday", 5, "17:00", "17:45"),
            ("monday", 5, "17:50", "18:35"),

            ("monday", 6, "18:45", "19:30"),
            ("monday", 6, "19:35", "20:20")
        ]

        saturday_times = [
            ("saturday", 1, "08:30", "09:15"),
            ("saturday", 1, "09:20", "10:05"),

            ("saturday", 2, "10:20", "11:05"),
            ("saturday", 2, "11:10", "11:55"),

            ("saturday", 3, "12:05", "12:50"),
            ("saturday", 3, "12:55", "13:40"),

            ("saturday", 4, "13:50", "14:35"),
            ("saturday", 4, "14:40", "15:25"),

            ("saturday", 5, "15:35", "16:20"),
            ("saturday", 5, "16:25", "17:10"),

            ("saturday", 6, "17:20", "18:05"),
            ("saturday", 6, "18:10", "18:55")
        ]

        cursor.executemany(
            "INSERT OR IGNORE INTO pair_times (day_type, pair_number, start_time, end_time) VALUES (?, ?, ?, ?)",
            weekday_times
        )
        cursor.executemany(
            "INSERT OR IGNORE INTO pair_times (day_type, pair_number, start_time, end_time) VALUES (?, ?, ?, ?)",
            monday_times
        )
        cursor.executemany(
            "INSERT OR IGNORE INTO pair_times (day_type, pair_number, start_time, end_time) VALUES (?, ?, ?, ?)",
            saturday_times
        )