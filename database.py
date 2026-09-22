import sqlite3
from sqlite3 import Row

DATABASE = "data/schedule.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = Row # строки из БД станут как словари - sqlite3.Row
    return conn