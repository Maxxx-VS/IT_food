"""
Файл определяет схемы Pydantic для валидации и
сериализации данных, используемых в API.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Базовая схема пользователя"""
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    """Схема для создания пользователя"""
    password: str = Field(..., min_length=8)
    role: Optional[str] = None

class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    username: str
    password: str

class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    password: Optional[str] = None
    role: Optional[str] = None

class UserResponse(UserBase):
    """Схема ответа с данными пользователя"""
    id: int
    role: str

    model_config = ConfigDict(from_attributes=True)

class RefreshToken(BaseModel):
    """Схема для Refresh Token"""
    refresh_token: str

class Token(BaseModel):
    """Схема JWT токена с Refresh Token"""
    access_token: str
    refresh_token: str
    token_type: str

class TestItemBase(BaseModel):
    """Базовая схема тестового элемента"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    value: int = Field(0, ge=0)

class TestItemCreate(TestItemBase):
    """Схема для создания элемента"""
    pass

class TestItemUpdate(BaseModel):
    """Схема для обновления элемента"""
    name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[int] = None

class TestItemResponse(TestItemBase):
    """Схема ответа с данными элемента"""
    id: int

    model_config = ConfigDict(from_attributes=True)

class CommentBase(BaseModel):
    """Базовая схема комментария"""
    content: str = Field(..., min_length=1, max_length=500)

class CommentCreate(CommentBase):
    """Схема для создания комментария"""
    pass

class CommentResponse(CommentBase):
    """Схема ответа с данными комментария"""
    id: int
    item_id: int
    author: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)