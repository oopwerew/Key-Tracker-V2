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
        taken_at TEXT,
        phone TEXT,
        expected_return TEXT
    )
    """)

    # Миграция колонок phone и expected_return, если база уже существовала
    cursor.execute("PRAGMA table_info(keys)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "phone" not in columns:
        cursor.execute("ALTER TABLE keys ADD COLUMN phone TEXT")
    if "expected_return" not in columns:
        cursor.execute("ALTER TABLE keys ADD COLUMN expected_return TEXT")

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

    # Таблица запросов на получение ключей (Пользователь -> Админ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS key_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_id TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        comment TEXT,
        expected_return TEXT,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'taken', 'cancelled')),
        admin_name TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
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
            ("101", "Компьютерный класс №1", 1, "ПК 1-15, проектор", "available", None, None, None, None),
            ("102", "Лекционная аудитория", 1, "100 мест, микрофон", "available", None, None, None, None),
            ("205", "Учительская / Кафедра", 2, "Главный вход", "taken", "Иванов Алексей Сергеевич", "2026-11-23 14:30", "+7(999)111-22-33", "до 18:00"),
            ("208", "Лаборатория физики", 2, "Стенды и оборудование", "available", None, None, None, None),
            ("304", "Конференц-зал", 3, "Экран, видеоконференция", "available", None, None, None, None),
            ("310", "Серверная комната", 3, "Доступ только IT-отделу", "taken", "Смирнов К.В.", "2026-11-23 16:15", "IT-отдел", "до конца дня"),
        ]
        cursor.executemany(
            "INSERT INTO keys (id, name, floor, notes, status, taken_by, taken_at, phone, expected_return) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            initial_keys
        )

        initial_history = [
            ("2026-11-23 14:30", "Выдача ключа", "205", "Учительская / Кафедра", "Иванов Алексей Сергеевич", "Выдан преподавателю (до 18:00)"),
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
def get_keys(search: str = None, status_filter: str = None):
    conn = get_connection()
    query = "SELECT * FROM keys WHERE 1=1"
    params = []

    if status_filter in ("available", "taken"):
        query += " AND status = ?"
        params.append(status_filter)

    if search and search.strip():
        search_term = f"%{search.strip().lower()}%"
        query += " AND (LOWER(id) LIKE ? OR LOWER(name) LIKE ? OR LOWER(IFNULL(taken_by, '')) LIKE ? OR LOWER(IFNULL(phone, '')) LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])

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
        return False, f"Кабинет с номером {key_id} уже существует!", None

    new_key = {
        "id": str(key_id).strip(),
        "name": name.strip(),
        "floor": floor,
        "notes": (notes or "").strip(),
        "status": "available",
        "taken_by": None,
        "taken_at": None,
        "phone": None,
        "expected_return": None
    }
    cursor.execute(
        "INSERT INTO keys (id, name, floor, notes, status) VALUES (?, ?, ?, ?, 'available')",
        (new_key["id"], new_key["name"], new_key["floor"], new_key["notes"])
    )
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Добавлен кабинет", new_key["id"], new_key["name"], "Администратор", "Создан в системе")
    )
    conn.commit()
    conn.close()
    return True, "Кабинет успешно добавлен", new_key

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
        "UPDATE key_requests SET status = 'cancelled', updated_at = ? WHERE key_id = ? AND status IN ('pending', 'approved')",
        (now_str, str(key_id).strip())
    )
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Удален кабинет", str(key_id).strip(), key["name"], "Администратор", "Удален из системы")
    )
    conn.commit()
    conn.close()
    return True, "Кабинет удален"

def issue_key(key_id: str, recipient_name: str, admin_name: str = "Администратор", phone: str = None, expected_return: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    key = conn.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone()
    if not key:
        conn.close()
        return False, "Кабинет не найден", None
    if key["status"] == "taken":
        conn.close()
        return False, f"Ключ уже выдан пользователю {key['taken_by']}", None

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "UPDATE keys SET status = 'taken', taken_by = ?, taken_at = ?, phone = ?, expected_return = ? WHERE id = ?",
        (recipient_name.strip(), now_str, phone.strip() if phone else None, expected_return.strip() if expected_return else None, str(key_id).strip())
    )
    cursor.execute(
        "UPDATE key_requests SET status = 'rejected', admin_name = ?, updated_at = ? WHERE key_id = ? AND status IN ('pending', 'approved')",
        (admin_name, now_str, str(key_id).strip())
    )
    details = f"Выдал: {admin_name}"
    if phone:
        details += f" • Тел/отдел: {phone.strip()}"
    if expected_return:
        details += f" • Возврат: {expected_return.strip()}"

    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Выдача ключа", str(key_id).strip(), key["name"], recipient_name.strip(), details)
    )
    conn.commit()
    updated_key = dict(conn.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone())
    conn.close()
    return True, "Ключ успешно выдан", updated_key

def return_key(key_id: str, admin_name: str = "Администратор", notes: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    key = conn.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone()
    if not key:
        conn.close()
        return False, "Кабинет не найден", None
    if key["status"] == "available":
        conn.close()
        return False, "Ключ уже в наличии", None

    prev_user = key["taken_by"] or "Не указан"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "UPDATE keys SET status = 'available', taken_by = NULL, taken_at = NULL, phone = NULL, expected_return = NULL WHERE id = ?",
        (str(key_id).strip(),)
    )
    details = f"Принял: {admin_name}"
    if notes:
        details += f" • Примечание: {notes.strip()}"

    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Возврат ключа", str(key_id).strip(), key["name"], prev_user, details)
    )
    conn.commit()
    updated_key = dict(conn.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone())
    conn.close()
    return True, "Ключ успешно возвращен", updated_key

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


# ==========================================
#       ЗАПРОСЫ ПОЛЬЗОВАТЕЛЕЙ НА КЛЮЧИ
# ==========================================

def create_key_request(key_id: str, user_id: int, user_name: str, comment: str = "", expected_return: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    key = cursor.execute("SELECT * FROM keys WHERE id = ?", (str(key_id).strip(),)).fetchone()
    if not key:
        conn.close()
        return False, "Кабинет не найден", None
    if key["status"] == "taken":
        conn.close()
        return False, f"Ключ уже на руках у пользователя {key['taken_by']}", None

    existing = cursor.execute(
        "SELECT * FROM key_requests WHERE key_id = ? AND user_id = ? AND status IN ('pending', 'approved')",
        (str(key_id).strip(), user_id)
    ).fetchone()
    if existing:
        conn.close()
        msg = "Ваш запрос уже одобрен администратором — вы можете взять ключ" if existing["status"] == "approved" else "Вы уже отправили запрос на этот ключ"
        return False, msg, None

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        """INSERT INTO key_requests (key_id, user_id, user_name, comment, expected_return, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (str(key_id).strip(), user_id, user_name.strip(), (comment or "").strip(), (expected_return or "").strip(), now_str, now_str)
    )
    req_id = cursor.lastrowid

    details = "Ожидает подтверждения администратора"
    if expected_return and expected_return.strip():
        details += f" • Возврат: {expected_return.strip()}"
    if comment and comment.strip():
        details += f" • {comment.strip()}"

    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Запрос ключа", str(key_id).strip(), key["name"], user_name.strip(), details)
    )
    conn.commit()
    new_req = dict(cursor.execute("""
        SELECT r.*, k.name AS key_name, k.floor AS key_floor
        FROM key_requests r
        LEFT JOIN keys k ON r.key_id = k.id
        WHERE r.id = ?
    """, (req_id,)).fetchone())
    conn.close()
    return True, "Запрос отправлен администратору", new_req

def get_requests(user_id: int = None, status_filter: str = None, limit: int = 100):
    conn = get_connection()
    query = """
        SELECT r.*, k.name AS key_name, k.floor AS key_floor, k.status AS key_status
        FROM key_requests r
        LEFT JOIN keys k ON r.key_id = k.id
        WHERE 1=1
    """
    params = []
    if user_id is not None:
        query += " AND r.user_id = ?"
        params.append(user_id)
    if status_filter and status_filter in ("pending", "approved", "rejected", "taken", "cancelled"):
        query += " AND r.status = ?"
        params.append(status_filter)

    query += " ORDER BY r.id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_request_by_id(req_id: int):
    conn = get_connection()
    row = conn.execute("""
        SELECT r.*, k.name AS key_name, k.floor AS key_floor, k.status AS key_status
        FROM key_requests r
        LEFT JOIN keys k ON r.key_id = k.id
        WHERE r.id = ?
    """, (req_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def approve_key_request(req_id: int, admin_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    req = cursor.execute("SELECT * FROM key_requests WHERE id = ?", (req_id,)).fetchone()
    if not req:
        conn.close()
        return False, "Запрос не найден", None
    if req["status"] != "pending":
        conn.close()
        return False, "Запрос уже обработан", None

    key = cursor.execute("SELECT * FROM keys WHERE id = ?", (req["key_id"],)).fetchone()
    if not key:
        conn.close()
        return False, "Кабинет не найден", None
    if key["status"] == "taken":
        conn.close()
        return False, f"Ключ уже на руках у {key['taken_by']}", None

    other_approved = cursor.execute(
        "SELECT id, user_name FROM key_requests WHERE key_id = ? AND status = 'approved' AND id != ?",
        (req["key_id"], req_id)
    ).fetchone()
    if other_approved:
        conn.close()
        return False, f"Этот ключ уже одобрен для пользователя {other_approved['user_name']}", None

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "UPDATE key_requests SET status = 'approved', admin_name = ?, updated_at = ? WHERE id = ?",
        (admin_name.strip(), now_str, req_id)
    )
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Запрос одобрен", req["key_id"], key["name"], req["user_name"], f"Одобрил: {admin_name.strip()}")
    )
    conn.commit()
    updated = dict(cursor.execute("SELECT * FROM key_requests WHERE id = ?", (req_id,)).fetchone())
    conn.close()
    return True, "Запрос подтверждён! Теперь пользователь сможет взять ключ.", updated

def reject_key_request(req_id: int, admin_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    req = cursor.execute("SELECT * FROM key_requests WHERE id = ?", (req_id,)).fetchone()
    if not req:
        conn.close()
        return False, "Запрос не найден", None
    if req["status"] not in ("pending", "approved"):
        conn.close()
        return False, "Нельзя отклонить уже завершённый запрос", None

    key = cursor.execute("SELECT * FROM keys WHERE id = ?", (req["key_id"],)).fetchone()
    key_name = key["name"] if key else ""

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "UPDATE key_requests SET status = 'rejected', admin_name = ?, updated_at = ? WHERE id = ?",
        (admin_name.strip(), now_str, req_id)
    )
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Запрос отклонён", req["key_id"], key_name, req["user_name"], f"Отклонил: {admin_name.strip()}")
    )
    conn.commit()
    updated = dict(cursor.execute("SELECT * FROM key_requests WHERE id = ?", (req_id,)).fetchone())
    conn.close()
    return True, "Запрос отклонён", updated

def take_approved_key(req_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    req = cursor.execute("SELECT * FROM key_requests WHERE id = ?", (req_id,)).fetchone()
    if not req:
        conn.close()
        return 404, "Запрос не найден", None
    if req["user_id"] != user_id:
        conn.close()
        return 403, "Доступ запрещён: это не ваш запрос", None
    if req["status"] != "approved":
        conn.close()
        if req["status"] == "pending":
            return 403, "Доступ запрещён: администратор ещё не подтвердил этот запрос", None
        return 400, "Запрос недействителен или уже использован", None

    key = cursor.execute("SELECT * FROM keys WHERE id = ?", (req["key_id"],)).fetchone()
    if not key:
        conn.close()
        return 404, "Кабинет не найден", None
    if key["status"] == "taken":
        conn.close()
        return 400, f"Ключ уже выдан пользователю {key['taken_by']}", None

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "UPDATE keys SET status = 'taken', taken_by = ?, taken_at = ?, expected_return = ? WHERE id = ?",
        (req["user_name"], now_str, req["expected_return"] or None, req["key_id"])
    )
    cursor.execute(
        "UPDATE key_requests SET status = 'taken', updated_at = ? WHERE id = ?",
        (now_str, req_id)
    )
    # Отклоняем остальные ожидающие заявки на этот ключ
    cursor.execute(
        "UPDATE key_requests SET status = 'rejected', admin_name = 'Система', updated_at = ? WHERE key_id = ? AND status = 'pending' AND id != ?",
        (now_str, req["key_id"], req_id)
    )

    details = f"Взято по одобренной заявке (Одобрил: {req['admin_name'] or 'Администратор'})"
    if req["expected_return"]:
        details += f" • Возврат: {req['expected_return']}"
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Выдача ключа", req["key_id"], key["name"], req["user_name"], details)
    )
    conn.commit()
    updated_key = dict(cursor.execute("SELECT * FROM keys WHERE id = ?", (req["key_id"],)).fetchone())
    conn.close()
    return 200, "Ключ успешно получен!", updated_key

def cancel_key_request(req_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    req = cursor.execute("SELECT * FROM key_requests WHERE id = ?", (req_id,)).fetchone()
    if not req:
        conn.close()
        return 404, "Запрос не найден"
    if req["user_id"] != user_id:
        conn.close()
        return 403, "Доступ запрещён: вы не можете отменить чужой запрос"
    if req["status"] not in ("pending", "approved"):
        conn.close()
        return 400, "Запрос уже завершён"

    key = cursor.execute("SELECT * FROM keys WHERE id = ?", (req["key_id"],)).fetchone()
    key_name = key["name"] if key else ""

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "UPDATE key_requests SET status = 'cancelled', updated_at = ? WHERE id = ?",
        (now_str, req_id)
    )
    cursor.execute(
        "INSERT INTO history (timestamp, action, key_id, key_name, user_name, details) VALUES (?, ?, ?, ?, ?, ?)",
        (now_str, "Отмена запроса", req["key_id"], key_name, req["user_name"], "Отменено пользователем")
    )
    conn.commit()
    conn.close()
    return 200, "Запрос отменён"
