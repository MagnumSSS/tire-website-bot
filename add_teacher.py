import pdfplumber
import requests
import sqlite3
import os
import re

standart_text = "https://www.ntmm.ru/institution/StrukturaOU/Педсостав/"

# шоб удобнее
ls_addr = {
    "11.02.16": f"{standart_text}11.02.16.pdf",
    "13.02.11-13": f"{standart_text}13.02.13%2013.02.11.pdf", 
    "15.01.05": f"{standart_text}15.01.05.pdf",
    "15.02.03": f"{standart_text}15.02.03.pdf",
    "15.02.05": f"{standart_text}15.02.05.pdf",
    "15.02.09": f"{standart_text}15.02.09.pdf",
    "15.02.10": f"{standart_text}15.02.10.pdf",
    "15.02.14": f"{standart_text}15.02.14.pdf",
    "15.02.12-17": f"{standart_text}15.02.17%2015.02.12.pdf",
    "15.02.11-18": f"{standart_text}15.02.18%2015.02.11%20.pdf",
    "22.02.06 - 15.02.19": f"{standart_text}15.02.19%2022.02.06.pdf",
    "27.02.07": f"{standart_text}27.02.07.pdf",
    "ОБЩ": f"{standart_text}общеобразовательный.pdf" # Метка для сортировки
}


def clean_cell(cell):
    if cell is None:
        return ""
    # split() и join() убирают все лишние пробелы и переносы строк
    text = " ".join(str(cell).split())
    # Убираем ТОЛЬКО запятые в конце, точки ОСТАВЛЯЕМ (они нужны для А.А.)
    text = text.rstrip(',')
    return text

def fix_broken_words(text):
    if not text:
        return text
    
    # Паттерн 1: Склейка разорванных ФИО
    # Теперь допускает отсутствие точки в конце или пробел между инициалами
    # "Скоробогато ва А.А" или "Скоробогато ва А. А." -> "Скоробогатова А.А."
    text = re.sub(r'([А-Яа-я]+)\s+([а-я]+)\s+([А-Я]\.?\s*[А-Я]\.?)', r'\1\2 \3', text)
    
    # Паттерн 2: Склейка разорванных слов в названиях (оставляем как было, он работает отлично)
    text = re.sub(r'([А-Яа-я]{5,})\s+([а-я]{1,3})\b', lambda m: m.group(1) + m.group(2), text)
    
    return text

# Подключаемся к БД
os.makedirs('data/pdf', exist_ok=True)
conn = sqlite3.connect('data/schedule.db')
cursor = conn.cursor()

# Создаем таблицу преподов (UNIQUE спасет от дублей при повторных запусках)
cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers (
    specialty TEXT NOT NULL,
    subject TEXT NOT NULL,
    teacher_name TEXT NOT NULL,
    position TEXT,
    UNIQUE(specialty, subject, teacher_name)
)
""")
conn.commit()

for specialty_label, url in ls_addr.items():
    print(f"Обрабатываем {specialty_label}...")
    file_path = f"data/pdf/teachers_{specialty_label}.pdf"
    
    # Кэширование: если файл уже скачан, не тратим время на сеть
    if not os.path.exists(file_path):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"PDF скачан")
        except Exception as e:
            print(f"Ошибка сети для {specialty_label}: {e}")
            continue
    else:
        print(f"Файл уже ест")

    try:
        with pdfplumber.open(file_path) as pdf:
            idx_subject = 0
            idx_name = 1
            idx_position = 2
            header_found = False
            prev_subject = ""
            
            for page in pdf.pages:
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 5,
                    "join_tolerance": 3,
                    "edge_min_length": 3,
                    "min_words_vertical": 3,
                    "min_words_horizontal": 1,
                    "text_tolerance": 1,      # было 3 по умолчанию
                    "text_x_tolerance": 1,
                    "text_y_tolerance": 1,
                })
                for table in tables:
                    for row in table:
                        if not row:
                            continue
                        
                        clean_row = [clean_cell(c) for c in row]
                        
                        # 1. Ищем шапку таблицы
                        if "Дисциплина" in clean_row and "ФИО" in clean_row:
                            idx_subject = clean_row.index("Дисциплина")
                            idx_name = clean_row.index("ФИО")
                            if "Должность" in clean_row:
                                idx_position = clean_row.index("Должность")
                            header_found = True
                            prev_subject = "" 
                            continue
                        
                        if not header_found:
                            continue
                        
        
                        
                        subject = fix_broken_words(clean_row[idx_subject]) if idx_subject < len(clean_row) else ""
                        teacher = fix_broken_words(clean_row[idx_name]) if idx_name < len(clean_row) else ""
                        position = clean_row[idx_position] if idx_position < len(clean_row) else ""

                                                # ГЛУБОКИЙ ШПИОН: показываем всю строку, если поймали подозрительное слово
                        if "Скоробогато" in teacher or "Абайдуленов" in teacher or "Материаловеде" in subject:
                            print(f"🕵️ ПОЙМАЛ ПОДОЗРИТЕЛЬНОЕ!")
                            print(f"   Subject: {repr(subject)}")
                            print(f"   Teacher: {repr(teacher)}")
                            print(f"   ВСЯ СТРОКА (clean_row): {clean_row}") # <-- ЭТО САМОЕ ВАЖНОЕ
                            print("-" * 50)

                        # ФИЛЬТР: если ФИО короткое (< 10 символов) и нет инициалов (точек) — это обрезок, скипаем
                        # Если имя <= 11 символов (как "Скоробогато") и в нем нет точек (инициалов) — это мусорный обрывок
                        if len(teacher) <= 11 and '.' not in teacher:
                            continue
                        # ФИЛЬТР: если ФИО начинается с маленькой буквы — это обрезок (вторая часть имени)
                        if teacher and teacher[0].islower():
                            continue
                        # ФИЛЬТР: если ФИО состоит только из инициалов (типа "И.В.") — это обрезок
                        if re.match(r'^[А-Я]\.[А-Я]\.?$', teacher):
                            continue

                        

                        # Forward fill для предмета
                        if not subject:
                            subject = prev_subject
                        else:
                            prev_subject = subject

                        if not subject and not teacher:
                            continue

                        # Сохраняем в БД
                        cursor.execute("""
                            INSERT OR REPLACE INTO teachers (specialty, subject, teacher_name, position)
                            VALUES (?, ?, ?, ?)
                        """, (specialty_label, subject, teacher, position))
                        
            conn.commit()
            print(f"Специальность {specialty_label} залита в БД!\n")
            
    except Exception as e:
        print(f"Ошибка парсинга PDF {specialty_label}: {e}")

conn.close()