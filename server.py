import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status, Depends, Response, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

import database
import auth

load_dotenv()
database.init_db()

app = FastAPI(
    title="Key Tracker V2 — Unified Backend",
    description="Единый бэкенд для веб-интерфейса, мобильного приложения (Flet) и десктопа",
    version="2.1.0"
)

# Разрешаем CORS для мобильных устройств, веб-браузеров и локальной сети
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Pydantic схемы
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2)
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)
    role: str = Field(..., pattern="^(user|admin)$")
    invite_code: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class AddKeyRequest(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=2)
    floor: int = 1
    notes: Optional[str] = ""

class IssueKeyRequest(BaseModel):
    recipient_name: Optional[str] = None
    user_name: Optional[str] = None
    phone: Optional[str] = None
    expected_return: Optional[str] = None

    def get_name(self) -> str:
        name = self.recipient_name or self.user_name
        return name.strip() if name else ""

class ReturnKeyRequest(BaseModel):
    notes: Optional[str] = None


# ==========================================
#               SYSTEM / HEALTH
# ==========================================

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "Key Tracker API v2.1 (Unified Backend)",
        "db": "connected"
    }


# ==========================================
#              АВТОРИЗАЦИЯ
# ==========================================

@app.post("/api/auth/register", tags=["Auth"])
def register(req: RegisterRequest, response: Response):
    if req.role == "admin":
        if not req.invite_code or req.invite_code.strip() != auth.ADMIN_INVITE_CODE.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Неверный код приглашения администратора. Регистрация администратора отклонена."
            )

    existing = database.get_user_by_username(req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует."
        )

    hashed = auth.hash_password(req.password)
    user_id = database.create_user(req.full_name, req.username, hashed, req.role)

    token = auth.create_access_token({"sub": str(user_id), "role": req.role, "name": req.full_name})
    response.set_cookie(key="auth_token", value=token, httponly=True, max_age=7*24*3600, samesite="lax")

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user_id,
            "full_name": req.full_name,
            "username": req.username,
            "role": req.role
        }
    }

@app.post("/api/auth/login", tags=["Auth"])
def login(req: LoginRequest, response: Response):
    user = database.get_user_by_username(req.username)
    if not user or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль."
        )

    token = auth.create_access_token({"sub": str(user["id"]), "role": user["role"], "name": user["full_name"]})
    response.set_cookie(key="auth_token", value=token, httponly=True, max_age=7*24*3600, samesite="lax")

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "username": user["username"],
            "role": user["role"]
        }
    }

@app.post("/api/auth/logout", tags=["Auth"])
def logout(response: Response):
    response.delete_cookie(key="auth_token")
    return {"status": "success", "message": "Вы успешно вышли из системы."}

@app.get("/api/auth/me", tags=["Auth"])
def get_me(user: dict = Depends(auth.get_current_user)):
    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "username": user["username"],
        "role": user["role"]
    }


# ==========================================
#      УНИФИЦИРОВАННЫЕ ЭНДПОИНТЫ КЛЮЧЕЙ
#   (Поддерживают и Веб-UI, и Мобилку Flet)
# ==========================================

@app.get("/stats", tags=["Keys"])
@app.get("/api/stats", tags=["Keys"])
def get_stats():
    return database.get_stats()

@app.get("/keys", tags=["Keys"])
@app.get("/api/keys", tags=["Keys"])
def list_keys(
    search: Optional[str] = Query(None),
    filter_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    selected_filter = filter_type or status or "all"
    return database.get_keys(search=search, status_filter=selected_filter)

@app.get("/keys/{key_id}", tags=["Keys"])
@app.get("/api/keys/{key_id}", tags=["Keys"])
def get_single_key(key_id: str):
    key = database.get_key_by_id(key_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ключ {key_id} не найден")
    return key

@app.post("/keys", status_code=status.HTTP_201_CREATED, tags=["Keys"])
@app.post("/api/keys", tags=["Keys"])
def add_new_key(req: AddKeyRequest, request: Request):
    # Проверка роли, если запрос идёт от веб-пользователя с токеном
    token = request.cookies.get("auth_token") or request.headers.get("Authorization")
    if token:
        try:
            curr_user = auth.decode_access_token(token.replace("Bearer ", ""))
            if curr_user.get("role") == "user":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён: требуются права администратора.")
        except Exception as e:
            if isinstance(e, HTTPException): raise e

    ok, msg, new_key = database.add_key(req.id, req.name, req.floor, req.notes or "")
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "success": True, "message": msg, "key": new_key}

@app.delete("/keys/{key_id}", tags=["Keys"])
@app.delete("/api/keys/{key_id}", tags=["Keys"])
def delete_key(key_id: str, request: Request):
    token = request.cookies.get("auth_token") or request.headers.get("Authorization")
    if token:
        try:
            curr_user = auth.decode_access_token(token.replace("Bearer ", ""))
            if curr_user.get("role") == "user":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён: требуются права администратора.")
        except Exception as e:
            if isinstance(e, HTTPException): raise e

    ok, msg = database.delete_key(key_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return {"status": "success", "success": True, "message": msg}

@app.post("/keys/{key_id}/issue", tags=["Keys"])
@app.post("/api/keys/{key_id}/issue", tags=["Keys"])
def issue_key_endpoint(key_id: str, req: IssueKeyRequest, request: Request):
    admin_name = "Администратор"
    token = request.cookies.get("auth_token") or request.headers.get("Authorization")
    if token:
        try:
            curr_user = auth.decode_access_token(token.replace("Bearer ", ""))
            if curr_user.get("role") == "user":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён: требуются права администратора.")
            admin_name = curr_user.get("name") or "Администратор"
        except Exception as e:
            if isinstance(e, HTTPException): raise e

    recipient = req.get_name()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Укажите ФИО получателя ключа")

    ok, msg, updated_key = database.issue_key(
        key_id=key_id,
        recipient_name=recipient,
        admin_name=admin_name,
        phone=req.phone,
        expected_return=req.expected_return
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "success": True, "message": msg, "key": updated_key}

@app.post("/keys/{key_id}/return", tags=["Keys"])
@app.post("/api/keys/{key_id}/return", tags=["Keys"])
def return_key_endpoint(key_id: str, request: Request, req: Optional[ReturnKeyRequest] = None):
    admin_name = "Администратор"
    token = request.cookies.get("auth_token") or request.headers.get("Authorization")
    if token:
        try:
            curr_user = auth.decode_access_token(token.replace("Bearer ", ""))
            if curr_user.get("role") == "user":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён: требуются права администратора.")
            admin_name = curr_user.get("name") or "Администратор"
        except Exception as e:
            if isinstance(e, HTTPException): raise e

    notes = req.notes if req else None
    ok, msg, updated_key = database.return_key(key_id=key_id, admin_name=admin_name, notes=notes)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "success": True, "message": msg, "key": updated_key}

@app.get("/history", tags=["History"])
@app.get("/api/history", tags=["History"])
def get_audit_log(request: Request, limit: int = 100):
    token = request.cookies.get("auth_token") or request.headers.get("Authorization")
    if token:
        try:
            curr_user = auth.decode_access_token(token.replace("Bearer ", ""))
            if curr_user.get("role") == "user":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён: журнал доступен только администраторам.")
        except Exception as e:
            if isinstance(e, HTTPException): raise e

    return database.get_history(limit=limit)


# ==========================================
#              ГЛАВНАЯ СТРАНИЦА (WEB UI)
# ==========================================

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🚀 Key Tracker V2 Unified Server запущен на http://localhost:{port}")
    uvicorn.run("server:app", host=host, port=port, reload=True)
