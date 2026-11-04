import pdfplumber
import requests
import sqlite3
import os

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

# Функция очистки ячейки от мусора и переносов строк
def clean_cell(cell):
    if cell is None:
        return ""
    return str(cell).replace('\n', ' ').replace('\r', '').replace('  ', ' ').strip()

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
                tables = page.extract_tables()
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
                        
                        
                        # 3. Достаем данные (с проверкой на выход за границы списка)
                        subject = clean_row[idx_subject] if idx_subject < len(clean_row) else ""
                        teacher = clean_row[idx_name] if idx_name < len(clean_row) else ""
                        position = clean_row[idx_position] if idx_position < len(clean_row) else ""
                        
                        # 4. Forward fill для предмета (если пустой - берем прошлый)
                        if not subject:
                            subject = prev_subject
                        else:
                            prev_subject = subject
                            
                        # Скипаем пустые строки
                        if not subject and not teacher:
                            continue
                            
                        # Защита от разбитых ФИО (типа "Е.В." без фамилии)
                        if ' ' not in teacher and len(teacher) < 6:
                            continue
                            
                        # 5. Сохраняем в БД
                        cursor.execute("""
                            INSERT OR REPLACE INTO teachers (specialty, subject, teacher_name, position)
                            VALUES (?, ?, ?, ?)
                        """, (specialty_label, subject, teacher, position))
                        
            conn.commit()
            print(f"Специальность {specialty_label} залита в БД!\n")
            
    except Exception as e:
        print(f"Ошибка парсинга PDF {specialty_label}: {e}")

conn.close()