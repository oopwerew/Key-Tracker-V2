import sqlite3
import os
from datetime import datetime
import bcrypt

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "keys.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
        created_at TEXT NOT NULL
    )
    """)

    # Таблица кабинетов/ключей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keys (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        floor INTEGER NOT NULL,
        notes TEXT,
        status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'taken')),
        taken_by TEXT,
        taken_at TEXT
    )
    """)

    # Таблица истории операций (Audit Log)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        action TEXT NOT NULL,
        key_id TEXT NOT NULL,
        key_name TEXT NOT NULL,
        user_name TEXT NOT NULL,
        details TEXT
    )
    """)
    conn.commit()

    # Проверяем, есть ли начальные пользователи
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Создаем администратора по умолчанию: admin / admin123
        admin_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            "INSERT INTO users (full_name, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            ("Главный Администратор", "admin", admin_hash, "admin", now_str)
        )
        # Создаем обычного пользователя по умолчанию: user / user123
        user_hash = bcrypt.hashpw("user123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            "INSERT INTO users (full_name, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            ("Иванов Алексей Сергеевич", "user", user_hash, "user", now_str)
        )
        conn.commit()

    # Проверяем, есть ли начальные кабинеты
    cursor.execute("SELECT COUNT(*) FROM keys")
    if cursor.fetchone()[0] == 0:
        initial_keys = [
            ("101", "Компьютерный класс №1", 1, "ПК 1-15, проектор", "available", None, None),
            ("102", "Лекционная аудитория", 1, "100 мест, микрофон", "available", None, None),
            ("205", "Учительская / Кафедра", 2, "Главный вход", "taken", "Иванов Алексей Сергеевич", "2026-11-23 14:30"),
            ("208", "Лаборатория физики", 2, "Стенды и оборудование", "available", None, None),
            ("304", "Конференц-зал", 3, "Экран, видеоконференция", "available", None, None),
            ("310", "Серверная комната", 3, "Доступ только IT-отделу", "taken", "Смирнов К.В.", "2026-11-23 16:15"),
        ]
        cursor.executemany(
            "INSERT INTO keys (id, name, floor, notes, status, taken_by, taken_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            initial_keys
        )

        initial_history = [
            ("2026-11-23 14:30", "Выдача ключа", "205", "Учительская / Кафедра", "Иванов Алексей Сергеевич", "Выдан преподавателю"),
            ("2026-11-23 16:15", "Выдача ключа", "310", "Серверная комната", "Смирнов К.В.", "Плановые работы")
        ]
        cursor.executemany(
            "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
            initial_history
        )
        conn.commit()

    conn.close()

# Функции пользователей
def get_user_by_username(username: str):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id: int):
    conn = get_connection()
    user = conn.execute("SELECT id, full_name, username, role, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(full_name: str, username: str, password_hash: str, role: str):
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (full_name, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (full_name.strip(), username.strip().lower(), password_hash, role, now_str)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

# Функции кабинетов
def get_keys(search: str = "", status_filter: str = "all"):
    conn = get_connection()
    query = "SELECT * FROM keys WHERE 1=1"
    params = []

    if status_filter in ("available", "taken"):
        query += " AND status = ?"
        params.append(status_filter)

    if search:
        search_term = f"%{search.strip().lower()}%"
        query += " AND (LOWER(id) LIKE ? OR LOWER(name) LIKE ? OR LOWER(IFNULL(taken_by, '')) LIKE ?)"
        params.extend([search_term, search_term, search_term])

    query += " ORDER BY CAST(id AS INTEGER), id ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_key_by_id(key_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None

def add_key(key_id: str, name: str, floor: int, notes: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM keys WHERE id = ?", (str(key_id).strip(),))
    if cursor.fetchone():
        conn.close()
        return False, f"Кабинет с номером {key_id} уже существует!"

    cursor.execute(
        "INSERT INTO keys (id, name, floor, notes, status) VALUES (?, ?, ?, ?, 'available')",
        (str(key_id).strip(), name.strip(), floor, notes.strip())
    )
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Добавлен кабинет", str(key_id).strip(), name.strip(), "Администратор", "Создан в системе")
    )
    conn.commit()
    conn.close()
    return True, "Кабинет успешно добавлен"

def delete_key(key_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    key = conn.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone()
    if not key:
        conn.close()
        return False, "Кабинет не найден"

    cursor.execute("DELETE FROM keys WHERE id = ?", (str(key_id).strip(),))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Удален кабинет", str(key_id).strip(), key["name"], "Администратор", "Удален из системы")
    )
    conn.commit()
    conn.close()
    return True, "Кабинет удален"

def issue_key(key_id: str, recipient_name: str, admin_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    key = conn.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone()
    if not key:
        conn.close()
        return False, "Кабинет не найден"
    if key["status"] == "taken":
        conn.close()
        return False, f"Ключ уже выдан пользователю {key['taken_by']}"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "UPDATE keys SET status = 'taken', taken_by = ?, taken_at = ? WHERE id = ?",
        (recipient_name.strip(), now_str, str(key_id).strip())
    )
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Выдача ключа", str(key_id).strip(), key["name"], recipient_name.strip(), f"Выдал: {admin_name}")
    )
    conn.commit()
    conn.close()
    return True, "Ключ успешно выдан"

def return_key(key_id: str, admin_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    key = conn.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone()
    if not key:
        conn.close()
        return False, "Кабинет не найден"
    if key["status"] == "available":
        conn.close()
        return False, "Ключ уже в наличии"

    prev_user = key["taken_by"] or "Не указан"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "UPDATE keys SET status = 'available', taken_by = NULL, taken_at = NULL WHERE id = ?",
        (str(key_id).strip(),)
    )
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Возврат ключа", str(key_id).strip(), key["name"], prev_user, f"Принял: {admin_name}")
    )
    conn.commit()
    conn.close()
    return True, "Ключ успешно возвращен"

def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
    taken = conn.execute("SELECT COUNT(*) FROM keys WHERE status = 'taken'").fetchone()[0]
    available = total - taken
    conn.close()
    return {
        "total": total,
        "available": available,
        "taken": taken
    }

def get_history(limit: int = 100):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
