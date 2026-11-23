import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "key_tracker.db")

DEFAULT_KEYS = [
    {
        "id": "101",
        "name": "Компьютерный класс №1",
        "floor": 1,
        "status": "available",
        "taken_by": None,
        "phone": None,
        "taken_at": None,
        "expected_return": None,
        "notes": "ПК 1-15, проектор"
    },
    {
        "id": "102",
        "name": "Лекционная аудитория",
        "floor": 1,
        "status": "available",
        "taken_by": None,
        "phone": None,
        "taken_at": None,
        "expected_return": None,
        "notes": "100 мест, микрофон"
    },
    {
        "id": "205",
        "name": "Учительская / Кафедра",
        "floor": 2,
        "status": "taken",
        "taken_by": "Иванов А.С.",
        "phone": "Кафедра физики / +7(999)111-22-33",
        "taken_at": "2026-11-23 14:30",
        "expected_return": "до 18:00",
        "notes": "Главный вход"
    },
    {
        "id": "208",
        "name": "Лаборатория физики",
        "floor": 2,
        "status": "available",
        "taken_by": None,
        "phone": None,
        "taken_at": None,
        "expected_return": None,
        "notes": "Стенды и оборудование"
    },
    {
        "id": "304",
        "name": "Конференц-зал",
        "floor": 3,
        "status": "available",
        "taken_by": None,
        "phone": None,
        "taken_at": None,
        "expected_return": None,
        "notes": "Экран, видеоконференция"
    },
    {
        "id": "310",
        "name": "Серверная комната",
        "floor": 3,
        "status": "taken",
        "taken_by": "Смирнов К.В.",
        "phone": "IT-отдел",
        "taken_at": "2026-11-23 16:15",
        "expected_return": "до конца дня",
        "notes": "Доступ только IT-отделу"
    }
]

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                floor INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                taken_by TEXT,
                phone TEXT,
                taken_at TEXT,
                expected_return TEXT,
                notes TEXT
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                key_id TEXT NOT NULL,
                key_name TEXT NOT NULL,
                user_name TEXT NOT NULL,
                details TEXT
            );
            """)

            # Seed initial keys if empty
            cursor.execute("SELECT COUNT(*) FROM keys")
            if cursor.fetchone()[0] == 0:
                for k in DEFAULT_KEYS:
                    cursor.execute("""
                    INSERT INTO keys (id, name, floor, status, taken_by, phone, taken_at, expected_return, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        k["id"], k["name"], k["floor"], k["status"],
                        k["taken_by"], k["phone"], k["taken_at"], k["expected_return"], k["notes"]
                    ))

                # Seed initial history
                cursor.execute("""
                INSERT INTO history (timestamp, action, key_id, key_name, user_name, details)
                VALUES ('2026-11-23 14:30', 'Выдача', '205', 'Учительская / Кафедра', 'Иванов А.С.', 'Срок: до 18:00 | Тел: +7(999)111-22-33')
                """)
                cursor.execute("""
                INSERT INTO history (timestamp, action, key_id, key_name, user_name, details)
                VALUES ('2026-11-23 16:15', 'Выдача', '310', 'Серверная комната', 'Смирнов К.В.', 'Срок: до конца дня | IT-отдел')
                """)
            conn.commit()

    def get_keys(self, search: Optional[str] = None, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM keys WHERE 1=1"
            params: list = []

            if status_filter and status_filter in ("available", "taken"):
                query += " AND status = ?"
                params.append(status_filter)

            if search:
                s = f"%{search.strip().lower()}%"
                query += " AND (LOWER(id) LIKE ? OR LOWER(name) LIKE ? OR LOWER(COALESCE(taken_by, '')) LIKE ?)"
                params.extend([s, s, s])

            query += " ORDER BY floor ASC, id ASC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_key_by_id(self, key_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM keys WHERE id = ?", (key_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def issue_key(
        self,
        key_id: str,
        user_name: str,
        phone: Optional[str] = None,
        expected_return: Optional[str] = None
    ) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM keys WHERE id = ?", (key_id,))
            row = cursor.fetchone()
            if not row:
                return False, f"Ключ с номером {key_id} не найден", None

            key_data = dict(row)
            if key_data["status"] == "taken":
                return False, f"Ключ {key_id} уже выдан пользователю {key_data.get('taken_by')}", None

            cursor.execute("""
            UPDATE keys
            SET status = 'taken', taken_by = ?, phone = ?, taken_at = ?, expected_return = ?
            WHERE id = ?
            """, (user_name.strip(), phone.strip() if phone else None, now_str, expected_return.strip() if expected_return else None, key_id))

            details_parts = []
            if phone:
                details_parts.append(f"Отдел/Тел: {phone.strip()}")
            if expected_return:
                details_parts.append(f"Срок: {expected_return.strip()}")
            details = " | ".join(details_parts) if details_parts else None

            cursor.execute("""
            INSERT INTO history (timestamp, action, key_id, key_name, user_name, details)
            VALUES (?, 'Выдача', ?, ?, ?, ?)
            """, (now_str, key_id, key_data["name"], user_name.strip(), details))

            conn.commit()

            cursor.execute("SELECT * FROM keys WHERE id = ?", (key_id,))
            return True, "Ключ успешно выдан", dict(cursor.fetchone())

    def return_key(self, key_id: str, notes: Optional[str] = None) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM keys WHERE id = ?", (key_id,))
            row = cursor.fetchone()
            if not row:
                return False, f"Ключ с номером {key_id} не найден", None

            key_data = dict(row)
            if key_data["status"] == "available":
                return False, f"Ключ {key_id} уже на месте (не был выдан)", None

            prev_user = key_data["taken_by"] or "Неизвестно"
            details = notes.strip() if notes else f"Возврат от {prev_user}"

            cursor.execute("""
            UPDATE keys
            SET status = 'available', taken_by = NULL, phone = NULL, taken_at = NULL, expected_return = NULL
            WHERE id = ?
            """, (key_id,))

            cursor.execute("""
            INSERT INTO history (timestamp, action, key_id, key_name, user_name, details)
            VALUES (?, 'Возврат', ?, ?, ?, ?)
            """, (now_str, key_id, key_data["name"], prev_user, details))

            conn.commit()

            cursor.execute("SELECT * FROM keys WHERE id = ?", (key_id,))
            return True, "Ключ успешно возвращен", dict(cursor.fetchone())

    def add_key(self, key_id: str, name: str, floor: int, notes: Optional[str] = None) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM keys WHERE id = ?", (key_id.strip(),))
            if cursor.fetchone():
                return False, f"Ключ с номером {key_id} уже существует", None

            cursor.execute("""
            INSERT INTO keys (id, name, floor, status, notes)
            VALUES (?, ?, ?, 'available', ?)
            """, (key_id.strip(), name.strip(), floor, notes.strip() if notes else None))

            cursor.execute("""
            INSERT INTO history (timestamp, action, key_id, key_name, user_name, details)
            VALUES (?, 'Добавлен ключ', ?, ?, 'Администратор', ?)
            """, (now_str, key_id.strip(), name.strip(), notes.strip() if notes else None))

            conn.commit()
            cursor.execute("SELECT * FROM keys WHERE id = ?", (key_id.strip(),))
            return True, "Кабинет успешно добавлен", dict(cursor.fetchone())

    def delete_key(self, key_id: str) -> tuple[bool, str]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM keys WHERE id = ?", (key_id,))
            row = cursor.fetchone()
            if not row:
                return False, f"Ключ с номером {key_id} не найден"

            key_data = dict(row)
            cursor.execute("DELETE FROM keys WHERE id = ?", (key_id,))
            cursor.execute("""
            INSERT INTO history (timestamp, action, key_id, key_name, user_name, details)
            VALUES (?, 'Удален ключ', ?, ?, 'Администратор', ?)
            """, (now_str, key_id, key_data["name"], "Удаление из базы"))
            conn.commit()
            return True, "Ключ успешно удален"

    def get_stats(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM keys")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM keys WHERE status = 'taken'")
            taken = cursor.fetchone()[0]

            return {
                "total": total,
                "taken": taken,
                "available": total - taken
            }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
