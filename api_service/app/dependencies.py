"""
Файл содержит зависимости, используемые в маршрутах FastAPI,
такие, как получение текущего пользователя из JWT токена и проверка
роли администратора.
"""

from fastapi import Depends, HTTPException, status
from .auth import oauth2_scheme, decode_token

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Получает текущего пользователя из JWT токена"""
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": payload["sub"], "role": payload.get("role", "user")}

def require_admin(user: dict = Depends(get_current_user)):
    """Проверяет права администратора"""
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user

def require_user(user: dict = Depends(get_current_user)):
    """Проверяет аутентификацию пользователя"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user
