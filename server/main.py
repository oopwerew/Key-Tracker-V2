import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from database import Database

app = FastAPI(
    title="Key Tracker API",
    description="REST API для учета и выдачи ключей администратором ресепшена (ПК и мобильная версия)",
    version="2.0.0"
)

# Разрешаем CORS для десктопа, мобильных клиентов и локальной сети
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()

# Pydantic модели
class IssueKeyRequest(BaseModel):
    user_name: str = Field(..., description="ФИО сотрудника или посетителя")
    phone: Optional[str] = Field(None, description="Отдел или номер телефона")
    expected_return: Optional[str] = Field(None, description="Ориентировочное время возврата (например: 'до 18:00')")

class ReturnKeyRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Примечание при возврате (опционально)")

class CreateKeyRequest(BaseModel):
    id: str = Field(..., description="Номер кабинета или идентификатор ключа")
    name: str = Field(..., description="Название кабинета / помещения")
    floor: int = Field(1, description="Этаж")
    notes: Optional[str] = Field(None, description="Примечание (оборудование, доп. инфо)")

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "Key Tracker API v2.0"}

@app.get("/keys", tags=["Keys"])
def get_keys(
    search: Optional[str] = Query(None, description="Поиск по номеру, названию или ФИО"),
    filter_type: Optional[str] = Query(None, description="Фильтр: all, available, taken")
):
    """Получить список всех ключей с поддержкой поиска и фильтрации"""
    status_filter = filter_type if filter_type in ("available", "taken") else None
    return db.get_keys(search=search, status_filter=status_filter)

@app.get("/keys/{key_id}", tags=["Keys"])
def get_key(key_id: str):
    """Получить информацию о конкретном ключе по номеру"""
    key = db.get_key_by_id(key_id)
    if not key:
        raise HTTPException(status_code=404, detail=f"Ключ {key_id} не найден")
    return key

@app.post("/keys/{key_id}/issue", tags=["Keys"])
def issue_key(key_id: str, payload: IssueKeyRequest):
    """Выдать ключ человеку (зафиксировать ФИО, телефон/отдел и срок)"""
    success, message, key = db.issue_key(
        key_id=key_id,
        user_name=payload.user_name,
        phone=payload.phone,
        expected_return=payload.expected_return
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message, "key": key}

@app.post("/keys/{key_id}/return", tags=["Keys"])
def return_key(key_id: str, payload: Optional[ReturnKeyRequest] = None):
    """Принять возврат ключа"""
    notes = payload.notes if payload else None
    success, message, key = db.return_key(key_id=key_id, notes=notes)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message, "key": key}

@app.get("/history", tags=["History"])
def get_history(limit: int = Query(50, ge=1, le=500)):
    """Получить журнал всех действий (выдачи, возвраты)"""
    return db.get_history(limit=limit)

@app.get("/stats", tags=["Stats"])
def get_stats():
    """Получить общую статистику по ключам (всего, доступно, на руках)"""
    return db.get_stats()

@app.post("/keys", status_code=status.HTTP_201_CREATED, tags=["Keys"])
def add_key(payload: CreateKeyRequest):
    """Добавить новый кабинет / ключ в систему"""
    success, message, key = db.add_key(
        key_id=payload.id,
        name=payload.name,
        floor=payload.floor,
        notes=payload.notes
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message, "key": key}

@app.delete("/keys/{key_id}", tags=["Keys"])
def delete_key(key_id: str):
    """Удалить кабинет / ключ из системы"""
    success, message = db.delete_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"success": True, "message": message}

if __name__ == "__main__":
    import uvicorn
    # Запуск сервера на 0.0.0.0:8000, чтобы мобильные клиенты могли подключаться по локальной сети
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
