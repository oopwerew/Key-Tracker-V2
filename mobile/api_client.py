import httpx
from typing import Optional, List, Dict, Any, Tuple
from config import DEFAULT_API_URL

class ApiClient:
    def __init__(self, base_url: str = DEFAULT_API_URL):
        self.base_url = base_url.rstrip("/")
        self.timeout = 5.0

    def set_base_url(self, new_url: str):
        self.base_url = new_url.rstrip("/")

    def check_health(self) -> Tuple[bool, str]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/health")
                if res.status_code == 200:
                    return True, "Сервер подключен"
                return False, f"Ошибка сервера: {res.status_code}"
        except httpx.ConnectError:
            return False, "Не удалось подключиться к серверу. Проверьте адрес и запущен ли сервер."
        except Exception as e:
            return False, f"Ошибка: {str(e)}"

    def get_keys(self, search: Optional[str] = None, filter_type: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]], str]:
        try:
            params = {}
            if search:
                params["search"] = search
            if filter_type and filter_type in ("available", "taken"):
                params["filter_type"] = filter_type

            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/keys", params=params)
                if res.status_code == 200:
                    return True, res.json(), ""
                return False, [], f"Ошибка получения ключей ({res.status_code})"
        except Exception as e:
            return False, [], f"Ошибка сети: {str(e)}"

    def get_stats(self) -> Tuple[bool, Dict[str, int], str]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/stats")
                if res.status_code == 200:
                    return True, res.json(), ""
                return False, {"total": 0, "available": 0, "taken": 0}, f"Ошибка: {res.status_code}"
        except Exception as e:
            return False, {"total": 0, "available": 0, "taken": 0}, f"Ошибка сети: {str(e)}"

    def issue_key(
        self,
        key_id: str,
        user_name: str,
        phone: Optional[str] = None,
        expected_return: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            payload = {
                "user_name": user_name,
                "phone": phone,
                "expected_return": expected_return
            }
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/keys/{key_id}/issue", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return True, data.get("message", "Ключ выдан")
                else:
                    detail = res.json().get("detail", "Ошибка выдачи ключа")
                    return False, detail
        except Exception as e:
            return False, f"Ошибка сети: {str(e)}"

    def return_key(self, key_id: str, notes: Optional[str] = None) -> Tuple[bool, str]:
        try:
            payload = {"notes": notes} if notes else None
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/keys/{key_id}/return", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return True, data.get("message", "Ключ возвращен")
                else:
                    detail = res.json().get("detail", "Ошибка возврата ключа")
                    return False, detail
        except Exception as e:
            return False, f"Ошибка сети: {str(e)}"

    def get_history(self, limit: int = 50) -> Tuple[bool, List[Dict[str, Any]], str]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/history", params={"limit": limit})
                if res.status_code == 200:
                    return True, res.json(), ""
                return False, [], f"Ошибка получения истории ({res.status_code})"
        except Exception as e:
            return False, [], f"Ошибка сети: {str(e)}"

    def add_key(self, key_id: str, name: str, floor: int, notes: Optional[str] = None) -> Tuple[bool, str]:
        try:
            payload = {
                "id": key_id,
                "name": name,
                "floor": floor,
                "notes": notes
            }
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/keys", json=payload)
                if res.status_code in (200, 201):
                    return True, "Кабинет успешно добавлен"
                else:
                    detail = res.json().get("detail", "Ошибка создания")
                    return False, detail
        except Exception as e:
            return False, f"Ошибка сети: {str(e)}"

    def delete_key(self, key_id: str) -> Tuple[bool, str]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.delete(f"{self.base_url}/keys/{key_id}")
                if res.status_code == 200:
                    return True, "Ключ удален"
                else:
                    detail = res.json().get("detail", "Ошибка удаления")
                    return False, detail
        except Exception as e:
            return False, f"Ошибка сети: {str(e)}"
