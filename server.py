import os
from fastapi import FastAPI, HTTPException, status, Depends, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

import database
import auth

load_dotenv()

database.init_db()

app = FastAPI(title="Key Tracker V2 API", version="2.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Схемы запросов
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
    floor: int
    notes: Optional[str] = ""

class IssueKeyRequest(BaseModel):
    recipient_name: str = Field(..., min_length=2)


# ==========================================
#              МАРШРУТЫ АВТОРИЗАЦИИ
# ==========================================

@app.post("/api/auth/register")
def register(req: RegisterRequest, response: Response):
    # Если выбран администратор, проверяем инвайт-код
    if req.role == "admin":
        if not req.invite_code or req.invite_code.strip() != auth.ADMIN_INVITE_CODE.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Неверный код приглашения администратора. Регистрация администратора отклонена."
            )

    # Проверяем, существует ли логин
    existing = database.get_user_by_username(req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует."
        )

    # Хэшируем пароль и создаем пользователя
    hashed = auth.hash_password(req.password)
    user_id = database.create_user(req.full_name, req.username, hashed, req.role)

    # Создаем токен
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

@app.post("/api/auth/login")
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

@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(key="auth_token")
    return {"status": "success", "message": "Вы успешно вышли из системы."}

@app.get("/api/auth/me")
def get_me(user: dict = Depends(auth.get_current_user)):
    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "username": user["username"],
        "role": user["role"]
    }


# ==========================================
#        МАРШРУТЫ КАБИНЕТОВ И КЛЮЧЕЙ
# ==========================================

@app.get("/api/stats")
def get_stats(user: dict = Depends(auth.get_current_user)):
    return database.get_stats()

@app.get("/api/keys")
def list_keys(search: str = "", status: str = "all", user: dict = Depends(auth.get_current_user)):
    return database.get_keys(search=search, status_filter=status)

@app.post("/api/keys")
def add_new_key(req: AddKeyRequest, admin: dict = Depends(auth.require_admin)):
    ok, msg = database.add_key(req.id, req.name, req.floor, req.notes or "")
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg}

@app.delete("/api/keys/{key_id}")
def delete_key(key_id: str, admin: dict = Depends(auth.require_admin)):
    ok, msg = database.delete_key(key_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return {"status": "success", "message": msg}

@app.post("/api/keys/{key_id}/issue")
def issue_key_endpoint(key_id: str, req: IssueKeyRequest, admin: dict = Depends(auth.require_admin)):
    ok, msg = database.issue_key(key_id, req.recipient_name, admin["full_name"])
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg}

@app.post("/api/keys/{key_id}/return")
def return_key_endpoint(key_id: str, admin: dict = Depends(auth.require_admin)):
    ok, msg = database.return_key(key_id, admin["full_name"])
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg}

@app.get("/api/history")
def get_audit_log(admin: dict = Depends(auth.require_admin)):
    return database.get_history()

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
    print(f"🚀 Key Tracker V2 запущен на http://localhost:{port}")
    uvicorn.run("server:app", host=host, port=port, reload=True)
