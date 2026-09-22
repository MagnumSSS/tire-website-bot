import pandas as pd

def parse_and_save_schedule(conn, group_name, day_week, file_path, run_id):
    day_offsets = {
        "ПН": 1,
        "ВТ": 7,
        "СР": 13,
        "ЧТ": 19,
        "ПТ": 25,
        "СБ": 31,
    } # создали таблицу смещений, относительно якоря

    # Читаем ВСЕ таблицы из HTML файла
    tables = pd.read_html(file_path)

    # tables — это список DataFrame'ов
    # tables[0] — первая таблица в файле
    df = tables[0]

    # наш индекс якоря, пока -1
    ancors_row = -1
    for row_idx in range(len(df)):
        # 1. fillna('') заменяет все NaN на пустые строки ""
        # 2..astype(str) гарантирует, что всё остальное тоже станет строкой

        # Превращаем все значения строки в строки и объединяем через пробел
        row_text = ' '.join(df.iloc[row_idx].fillna('').astype(str))

        if "н/п" in row_text and "Дисциплина" in row_text and "каб" in row_text:
            ancors_row = row_idx
            print(f"🎯 Якорь найден в строке {ancors_row}!")
            break

    # Проверка на случай, если таблица вообще кривая и якоря нет
    if ancors_row == -1:
        print("❌ Ошибка: Якорь не найден. Структура таблицы сломана.")
        return


    # строка с группами
    groups = df.iloc[ancors_row-1]


    # считаем старт сложив расположение якоря + смещение
    offset = day_offsets.get(day_week, -1)
    if offset == -1 :
        print("Неправильный день")
        return
    start_room = ancors_row + offset

    # eq сравнивает каждый элемент со строкой group_name в итоге будет в строке будет 3 колонки с нашей группой(инфа от pandas_parser2)
    # и вот тут нужен idmax который вернет id можно сказать первого совпадения
    start_col = groups.eq(group_name).idxmax()

    if groups[start_col] != group_name:
        print("Неправильная группа")
        return 


    # флаг для проверки повторяющихся пар, у которых нет номера кабинета
    prev_room = None

    # Только для отладки?
    #print(f"Расписание в группе {group_name} в {day_week}: ")
    cursor = conn.cursor()

    # print(f"  [DEBUG] Начинаем цикл. start_room={start_room}, start_col={start_col}")

    for i in range(start_room, start_room+6):
        data = df.iloc[i, start_col:start_col+3] # i - строка, start_col:start_col+3 - ячейка
        if pd.isna(data.iloc[1]):
            # print(f"  [skip] Строка {i}: предмет пустой")
            continue 

        pair = data.iloc[0]
        pair = int(pair) if not pd.isna(pair) else 0

        # Проверка кабинета пары
        room = data.iloc[2]
        if pd.isna(room):
            if prev_room is not None:
                room = prev_room # Используем кабинет из предыдущей строки
            else:
                room = "Отсутствует"
        else:
            prev_room = room # Запоминаем текущий кабинет для следующих строк

        # print(f"  [INSERT] pair={pair}, subject='{data.iloc[1]}', room='{room}'")

        cursor.execute("""
            INSERT OR REPLACE INTO schedule 
            (group_name, day_of_week, pair_number, subject, room, run_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (group_name, day_week, pair, data.iloc[1], room, run_id))

        # print(f"  [DEBUG] cursor.rowcount = {cursor.rowcount}")

    # # DEBUG       
    # print(f"  [DEBUG] Цикл завершен. Проверяем данные в БД...")
    # cursor.execute("SELECT COUNT(*) FROM schedule WHERE group_name = ?", (group_name,))
    # count = cursor.fetchone()[0]
    # print(f"  [DEBUG] Записей в БД для {group_name}: {count}")
    


