from fastapi import FastAPI, Query, HTTPException
from database import get_db
from datetime import datetime

from pydantic import BaseModel
from typing import List
from typing import Optional

from fastapi.middleware.cors import CORSMiddleware

# Функция для проверки валидности кабинета
import re
def is_valid_room(room):
    # Пропускаем "с/з", "ДП/з" и т.д.
    if not room or room in ['с/з', 'ДП/з', 'Отсутствует']:
        return False
    
    # Извлекаем числовую часть (например, "201а" → 201)
    match = re.match(r'^(\d+)', room)
    if match:
        room_number = int(match.group(1))
        return room_number <= 600  # Убираем всё, что больше 600
    return False

# 0) Создаем модель ответа (как структура в Си)
class Lesson(BaseModel):
    pair: int
    subject: str
    room: str # первая структура, пара - урок - кабинет

class ScheduleResponse(BaseModel):
    group: str
    day: str
    lessons: List[Lesson] # вторая структура группа - день - первая структура

# 1) Создаем приложение - это наш продавец
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки — любой домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# !! ВСЕ ЭТО Огромный блок, начиная с app.get заканчивая return !!
# 2) Создаем эндпоинт (маршрут) — это "полка", с которой клиент может взять товар
# 2.1) Используем модель в эндпоинте
@app.get("/api/schedule", response_model=ScheduleResponse)
# @app.get("/api/schedule") — это декоратор. Он говорит FastAPI: "Когда кто-то сделает GET-запрос по адресу /api/schedule, вызови функцию ниже". 
# GET — это метод HTTP для получения данных (как "показать" в браузере).
def get_schedule(
    group: str = Query(..., description="Название группы, например АТ-381"),
    day: str = Query(..., description="День недели, например ПН")
):  
    # 3) Пока возвращаем то, что прислал клиент
    # return {...} - функция возвращает словарь. FastAPI автоматически превратит его в JSON.
    # return {
    #     "group": group,
    #     "day": day,
    #     "message": "Пока тут заглушка"
    # } - ЭТО пока заглушка, без обращения к БД
    conn = get_db()
    cursor = conn.cursor()

    # ЗАПРОС К БД
    # AS pair потому что Pydantic ждет pair, ведь в классе Lesson прописано именно так
    cursor.execute("""
        SELECT pair_number AS pair, subject, room 
        FROM schedule 
        WHERE group_name = ? AND day_of_week = ?
        ORDER BY pair_number ASC
    """, (group, day)) # в функции передаем group, day и в зависимости от данных, отдаем нужное расписание

    rows = cursor.fetchall() # без Row был бы кортеж, а у нас словарь
    conn.close()

    if not rows:
        # Если ничего не нашли - 404
        raise HTTPException(status_code=404, detail=f"Расписание для {group} на {day} не найдено")

    return {
        "group": group,
        "day": day,
        "lessons": [dict(row) for row in rows] # Превращаем Row в dict
    }

# Второй эндпоинт
@app.get("/api/last_update")
def get_last_update():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT start_time, end_time 
        FROM parser_runs 
        WHERE status = 'success' 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        # Если таблица пустая (парсер еще ни разу не запускался)
        return {"message": "Расписание еще не обновлялось"}
        
    # 2. Форматируем ответ
    # row["start_time"] и row["end_time"] будут строками вида "2024-01-15 14:00:00"
    # Нам нужно отрезать секунды и оставить только часы и минуты (например, "14:00")
    
    start_time = row["start_time"][11:16] # Берем с 11 по 16 символ (ЧЧ:ММ)
    end_time = row["end_time"][11:16]
    
    return {
        "updated_between": f"{start_time} - {end_time}"
    }

# выдача расписания по дням
@app.get("/api/pair_times")
def get_pair_times(day_type: str = Query(...)):
    """
    day_type: 'weekday' (ВТ-ПТ), 'monday' (ПН), или 'saturday' (СБ)
    """
    # это docstring (документационная строка).

    conn = get_db()
    cursor = conn.cursor()

    # ЧТО ПРОСИМ (SELECT)
    # У КОГО ПРОСИМ (FROM)
    # СУЖАЕМ ПОИСК ПРОШЕНИЯ ПО УСЛОВИЮ (WHERE)
    # СОРТИРУЕМ РЕЗУЛЬТА ПО ВОЗРАСТАНИЮ (ASC)
    cursor.execute("""
        SELECT pair_number, start_time, end_time 
        FROM pair_times
        WHERE day_type = ?
        ORDER BY pair_number ASC
    """, (day_type,))

    rows = cursor.fetchall()
    conn.close()
    times = {}
    for row in rows:
        pair_num = row["pair_number"]
        if pair_num not in times:
            times[pair_num] = []
        times[pair_num].append({
            "start": row["start_time"],
            "end": row["end_time"] # обращение по ключам
        })    

    return {
        "day_type": day_type,
        "times": times
    }

# отдаем список групп
@app.get("/api/groups")
def get_groups():
    conn = get_db() # кастомная функция чтобы не вызывать with
    cursor = conn.cursor()

    cursor.execute("""
        SELECT group_name
        FROM groups
        ORDER BY group_name ASC
    """)

    rows = cursor.fetchall()
    conn.close()
    group_list = [row["group_name"] for row in rows]

    return {
        "groups": group_list
    }

# свободные комнаты в какой то день и в какую то пару
@app.get("/api/free_rooms")
def get_free_rooms(
    day: str = Query(..., description="Предполагаемый день"),
    pair: str = Query(..., description="Предполагаемая пара")
):
    conn = get_db()
    cursor = conn.cursor()

    # все кабинеты
    cursor.execute("""
        SELECT DISTINCT room 
        FROM schedule 
        WHERE room != 'Отсутствует'
    """)
    # как в прошлом эндпоинте используем такую стратегию
    # Выражение (expression) - row["room"] — то, что будет добавлено в новый список для каждого элемента
    all_rooms = set(row["room"] for row in cursor.fetchall())

    # теперь именно занятые пары
    cursor.execute("""
        SELECT DISTINCT room
        FROM schedule
        WHERE day_of_week = ? AND pair_number = ? AND room != 'Отсутствует'
    """, (day, pair))
    busy_rooms = set(row['room'] for row in cursor.fetchall())

    # просто вычитаем элементы из списка
    free_rooms = list(all_rooms - busy_rooms)
    # фильтруем список
    free_rooms = [room for room in free_rooms if is_valid_room(room)]
    # сортируем по возрастанию
    free_rooms.sort(key=lambda x: int(re.match(r'(\d+)', x).group(1)) if re.match(r'(\d+)', x) else 9999)
    return {
        "day": day,
        "pair": pair,
        "free_rooms": free_rooms
    }

# совмещенки
@app.get("/api/combined_classes")
def get_combined_classes(
    subject: Optional[str] = Query(None), # теперь тоже опционально
    day_week: str = Query(...),
    pair_num: Optional[str] = Query(None), # опциональный 
    room: Optional[str] = Query(None) # опциональный 
):      
    # ВАЛИДАЦИЯ: хотя бы один из subject или room должен быть передан
    if not subject and not room:
        raise HTTPException(
            status_code=400, 
            detail="Нужно указать хотя бы предмет или кабинет"
        )
    
    # ЧТО ПРОСИМ(SELECT)
    # У КОГО ПРОСИМ(FROM)
    # СУЖАЕМ ПОИСК ПО УСЛОВИЮ, теперь не просто строгое: = ?, а похожее: LIKE ?
    
    query = """
        SELECT group_name, day_of_week, pair_number, subject, room
        FROM schedule
        WHERE day_of_week = ?
    """
    params = [day_week]

    # Логика: (предмет ИЛИ кабинет) + день
    # Если переданы оба - ищем по обоим через OR
    # Если только один - ищем только по нему

    conditions = []

    # Добавляем условие, если параметр передан

    if subject:
        conditions.append("subject LIKE ?")
        params.append(f"%{subject}%")

    if room:
        conditions.append("room LIKE ?")
        params.append(f"%{room}%")
    
    # Объединяем условия через OR
    if conditions:
        query += " AND (" + " OR ".join(conditions) + ")"
    
    # Добавляем опциональный фильтр по паре
    if pair_num is not None:
        query += " AND pair_number = ?"
        params.append(pair_num)

    query += " ORDER BY group_name, day_of_week, pair_number "
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall() # возвращает сырые sqlite3.Row, могло быть хуже
    conn.close()

    return {
        "query": subject or room,
        "groups": [dict(row) for row in rows]
    }


# api для старого расписани

@app.get("/api/schedule_snapshot")
def get_schedule_snapshot(
    group: str = Query(..., description="Название группы"),
    day: str = Query(..., description="День недели")
):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT pair_number AS pair, subject, room 
        FROM schedule_snapshot
        WHERE group_name = ? AND day_of_week = ?
        ORDER BY pair_number ASC
    """, (group, day)) # в функции передаем group, day и в зависимости от данных, отдаем нужное расписание

    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail="Снапшот не найден")
    
    return {
        "group": group,
        "day": day,
        "lessons": [dict(row) for row in rows]
    }

@app.get("/api/has_changes")
def check_changes(
    group: str = Query(...),
    day: str = Query(...)
):
    conn = get_db()
    cursor = conn.cursor()

    # Ищем строки, которые есть в текущем расписании, но отсутствуют в снапшоте
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT group_name, pair_number, day_of_week, subject, room 
            FROM schedule 
            WHERE group_name = ? AND day_of_week = ?
            EXCEPT
            SELECT group_name, pair_number, day_of_week, subject, room 
            FROM schedule_snapshot 
            WHERE group_name = ? AND day_of_week = ?
        )
    """, (group, day, group, day))

    diff_count = cursor.fetchone()[0]
    conn.close()

    # if diff_count > 0, значит есть отличия
    return{"has_changes": diff_count > 0}


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}