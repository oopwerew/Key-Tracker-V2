import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "keys.json")

DEFAULT_KEYS = [
    {
        "id": "101",
        "name": "Компьютерный класс №1",
        "floor": 1,
        "status": "available",
        "taken_by": None,
        "taken_at": None,
        "notes": "ПК 1-15, проектор"
    },
    {
        "id": "102",
        "name": "Лекционная аудитория",
        "floor": 1,
        "status": "available",
        "taken_by": None,
        "taken_at": None,
        "notes": "100 мест, микрофон"
    },
    {
        "id": "205",
        "name": "Учительская / Кафедра",
        "floor": 2,
        "status": "taken",
        "taken_by": "Иванов А.С.",
        "taken_at": "2026-11-23 14:30",
        "notes": "Главный вход"
    },
    {
        "id": "208",
        "name": "Лаборатория физики",
        "floor": 2,
        "status": "available",
        "taken_by": None,
        "taken_at": None,
        "notes": "Стенды и оборудование"
    },
    {
        "id": "304",
        "name": "Конференц-зал",
        "floor": 3,
        "status": "available",
        "taken_by": None,
        "taken_at": None,
        "notes": "Экран, видеоконференция"
    },
    {
        "id": "310",
        "name": "Серверная комната",
        "floor": 3,
        "status": "taken",
        "taken_by": "Смирнов К.В.",
        "taken_at": "2026-11-23 16:15",
        "notes": "Доступ только IT-отделу"
    }
]

class KeyStorage:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.keys = []
        self.history = []
        self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.keys = data.get("keys", [])
                    self.history = data.get("history", [])
                    return
            except Exception as e:
                print(f"Ошибка загрузки данных: {e}")
        
        # Если файла нет — создаем с базовым набором
        self.keys = list(DEFAULT_KEYS)
        self.history = [
            {
                "timestamp": "2026-11-23 14:30",
                "action": "Выдача",
                "key_id": "205",
                "key_name": "Учительская / Кафедра",
                "user_name": "Иванов А.С."
            },
            {
                "timestamp": "2026-11-23 16:15",
                "action": "Выдача",
                "key_id": "310",
                "key_name": "Серверная комната",
                "user_name": "Смирнов К.В."
            }
        ]
        self.save()

    def save(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"keys": self.keys, "history": self.history}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")

    def get_keys(self, search="", filter_type="all"):
        result = []
        search_lower = search.strip().lower()

        for k in self.keys:
            # Поиск по номеру или названию
            matches_search = (
                not search_lower or 
                search_lower in k["id"].lower() or 
                search_lower in k["name"].lower() or
                (k["taken_by"] and search_lower in k["taken_by"].lower())
            )
            if not matches_search:
                continue

            # Фильтрация
            if filter_type == "available" and k["status"] != "available":
                continue
            elif filter_type == "taken" and k["status"] != "taken":
                continue

            result.append(k)
        return result

    def take_key(self, key_id, user_name):
        for k in self.keys:
            if k["id"] == key_id:
                if k["status"] == "taken":
                    return False, "Ключ уже выдан!"
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                k["status"] = "taken"
                k["taken_by"] = user_name.strip()
                k["taken_at"] = now_str

                self.history.insert(0, {
                    "timestamp": now_str,
                    "action": "Взят пользователем",
                    "key_id": k["id"],
                    "key_name": k["name"],
                    "user_name": user_name.strip()
                })
                self.save()
                return True, "Ключ успешно получен!"
        return False, "Ключ не найден"

    def return_key(self, key_id):
        for k in self.keys:
            if k["id"] == key_id:
                if k["status"] == "available":
                    return False, "Ключ уже на месте"
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                prev_user = k["taken_by"]
                k["status"] = "available"
                k["taken_by"] = None
                k["taken_at"] = None

                self.history.insert(0, {
                    "timestamp": now_str,
                    "action": "Возврат",
                    "key_id": k["id"],
                    "key_name": k["name"],
                    "user_name": prev_user or "Неизвестно"
                })
                self.save()
                return True, "Ключ успешно возвращен!"
        return False, "Ключ не найден"

    def add_key(self, key_id, name, floor, notes=""):
        # Проверяем, существует ли уже такой кабинет
        for k in self.keys:
            if k["id"] == str(key_id).strip():
                return False, f"Кабинет с номером {key_id} уже существует!"

        new_key = {
            "id": str(key_id).strip(),
            "name": name.strip(),
            "floor": floor,
            "status": "available",
            "taken_by": None,
            "taken_at": None,
            "notes": notes.strip()
        }
        self.keys.append(new_key)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.history.insert(0, {
            "timestamp": now_str,
            "action": "Добавлен ключ",
            "key_id": new_key["id"],
            "key_name": new_key["name"],
            "user_name": "Администратор"
        })
        self.save()
        return True, "Кабинет успешно добавлен!"

    def delete_key(self, key_id):
        for i, k in enumerate(self.keys):
            if k["id"] == key_id:
                deleted = self.keys.pop(i)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.history.insert(0, {
                    "timestamp": now_str,
                    "action": "Удален ключ",
                    "key_id": deleted["id"],
                    "key_name": deleted["name"],
                    "user_name": "Администратор"
                })
                self.save()
                return True, "Ключ удален!"
        return False, "Ключ не найден"

    def get_stats(self):
        total = len(self.keys)
        taken = sum(1 for k in self.keys if k["status"] == "taken")
        available = total - taken
        return {
            "total": total,
            "available": available,
            "taken": taken
        }

    def get_history(self, limit=50):
        return self.history[:limit]
