import requests
import time
import pandas as pd
import os
import sqlite3

# я понял! мы вызываем имя файла, в котором есть нужные функции и чтобы использовать функцию надо написать имя_файла.функция
import ini_sql

def ini_parser_groups():
    path = "data/schedule.db"

    if not os.path.exists(path):
        ini_sql.ini_db()


    group_links = {}


    for i in range(1, 9):
        url_site = f"https://ntmm.ru/incoming/R-OO/{i}_screen.files/sheet001.htm"

        if i == 2:
            url_site = f"https://ntmm.ru/incoming/R-OO/{i}_screen1.files/sheet001.htm"
        try:
            # получаем нужную страничку
            response = requests.get(url_site)
            # проверка на 400/500 ошибки
            response.raise_for_status()

            with open(f'data/raw_schedule{i}.html', 'w', encoding='utf-8') as f:
                f.write(response.text)

            print(f"Страница получена! Статус: {response.status_code}")

            # Читаем ВСЕ таблицы из HTML файла
            tables = pd.read_html(f'data/raw_schedule{i}.html')

            # tables — это список DataFrame'ов
            # tables[0] — первая таблица в файле
            df = tables[0]

            # наш индекс якоря, пока -1
            anchor_row = -1

            # ищем якорь в виде строки с Дисциплина и т.д.
            for row_idx in range(len(df)):
                # 1. fillna('') заменяет все NaN на пустые строки ""
                # 2..astype(str) гарантирует, что всё остальное тоже станет строкой
                # Превращаем все значения строки в строки и объединяем через пробел
                row_text = ' '.join(df.iloc[row_idx].fillna('').astype(str))

                if "н/п" in row_text and "Дисциплина" in row_text and "каб" in row_text:
                    anchor_row = row_idx
                    print(f"🎯 Якорь найден в строке {anchor_row}!")
                    break

            # Проверка на случай, если таблица вообще кривая и якоря нет
            if anchor_row == -1:
                print("❌ Ошибка: Якорь не найден. Структура таблицы сломана.")
                continue

            groups = df.iloc[anchor_row - 1, 2:]
            # 3. .dropna() мгновенно удаляет все пустые ячейки (NaN)
            # 4. .unique() оставляет только уникальные названия (убирает дубликаты, если группа занимала 3 колонки)
            clean_groups = groups.dropna().unique()

            print(f"[*] В файле {i} найдено групп: {len(clean_groups)}")
            # 4. Теперь спокойно проходимся по чистому списку
            for group_name in clean_groups:
                # Превращаем название в строку на всякий случай и добавляем в словарь
                group_links[str(group_name)] = f"raw_schedule{i}.html"


            time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"Код ошибки сети {e}")
        except IOError as e:
            print(f"Ошибка записи файла {e}")

    for group_name, group_file in group_links.items():
        # подключаемся к бд
        with sqlite3.connect('data/schedule.db') as conn:
            # создаем курсор
            cursor = conn.cursor()

            cursor.execute(
                "INSERT OR IGNORE INTO groups (group_name, file_path) VALUES (?, ?)",
                (group_name, group_file)
            )

            # conn.commit() будет автоматом, ибо используем with