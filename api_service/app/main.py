"""
Является основным файлом приложения,
в котором определены маршруты API и логика обработки запросов.
"""


from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query
from . import schemas, crud, dependencies
from .database import get_db, engine, Base
from .auth import create_refresh_token
from .models import TestTable
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import pandas as pd
from pydantic import ValidationError
import tempfile
import os

app = FastAPI(
    title="Enhanced FastAPI Application",
    description="Универсальное приложение с аутентификацией и CRUD операциями",
    version="1.0.0"
)

# Регистрация пользователя
@app.post("/register", response_model=schemas.Token)
async def register(
        user: schemas.UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя"""
    existing_user = await crud.get_user(db, user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    users = await crud.get_users(db)
    role = "admin" if len(users) == 0 else "user"

    db_user = await crud.create_user(db, schemas.UserCreate(
        username=user.username,
        password=user.password,
        role=role
    ))

    access_token = crud.auth.create_access_token(
        data={"sub": user.username, "role": role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )
    await crud.create_refresh_token(
        db,
        user_id=db_user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# Вход пользователя
@app.post("/login", response_model=schemas.Token)
async def login(
        user: schemas.UserLogin,
        db: AsyncSession = Depends(get_db)
):
    """Аутентификация пользователя"""
    db_user = await crud.get_user(db, user.username)
    if not db_user or not crud.auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token = crud.auth.create_access_token(
        data={"sub": user.username, "role": db_user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )
    await crud.create_refresh_token(
        db,
        user_id=db_user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# Обновление токена
@app.post("/refresh", response_model=schemas.Token)
async def refresh_access_token(
    refresh_token: schemas.RefreshToken,
    db: AsyncSession = Depends(get_db)
):
    """Обновление Access Token с помощью Refresh Token"""
    payload = crud.auth.verify_refresh_token(refresh_token.refresh_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    db_token = await crud.get_refresh_token(db, refresh_token.refresh_token)
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid"
        )

    user = await crud.get_user(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    await crud.delete_refresh_token(db, refresh_token.refresh_token)

    access_token = crud.auth.create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user.username}
    )
    await crud.create_refresh_token(
        db,
        user_id=user.id,
        token=new_refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

# Получение списка пользователей (admin)
@app.get("/users/", response_model=list[schemas.UserResponse])
async def read_users(
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db),
        admin: dict = Depends(dependencies.require_admin)
):
    """Получение списка пользователей (только для администраторов)"""
    return await crud.get_users(db, skip=skip, limit=limit)

# Получение информации о пользователе
@app.get("/users/{username}", response_model=schemas.UserResponse)
async def read_user(
        username: str,
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(dependencies.get_current_user)
):
    """Получение информации о пользователе"""
    if current_user["role"] != "admin" and current_user["username"] != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile or admin can view any"
        )
    user = await crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Обновление пользователя
@app.patch("/users/{username}", response_model=schemas.UserResponse)
async def update_user(
        username: str,
        user_update: schemas.UserUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(dependencies.get_current_user)
):
    """Обновление данных пользователя"""
    if current_user["role"] != "admin" and current_user["username"] != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )

    updated_user = await crud.update_user(db, username, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user

# Удаление пользователя (admin)
@app.delete("/users/{username}")
async def delete_user(
        username: str,
        db: AsyncSession = Depends(get_db),
        admin: dict = Depends(dependencies.require_admin)
):
    """Удаление пользователя (только для администраторов)"""
    if not await crud.delete_user(db, username):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User deleted successfully"}

# Выход пользователя
@app.post("/logout")
async def logout(
        refresh_token: schemas.RefreshToken,
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(dependencies.require_user)
):
    """Выход пользователя"""
    await crud.delete_refresh_token(db, refresh_token.refresh_token)
    return {"message": "Logged out successfully"}

# Информация о текущем пользователе
@app.get("/me", response_model=schemas.UserResponse)
async def read_current_user(
        current_user: dict = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Получение информации о текущем пользователе"""
    user = await crud.get_user(db, current_user["username"])
    return user

# Обновление текущего пользователя
@app.patch("/me", response_model=schemas.UserResponse)
async def update_current_user(
        user_update: schemas.UserUpdate,
        current_user: dict = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Обновление информации о текущем пользователе"""
    updated_user = await crud.update_user(db, current_user["username"], user_update)
    return updated_user

# Удаление текущего пользователя
@app.delete("/me")
async def delete_current_user(
        current_user: dict = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Удаление текущего пользователя"""
    await crud.delete_user(db, current_user["username"])
    return {"message": "User deleted successfully"}

# Создание одного тестового элемента
@app.post("/items/", response_model=schemas.TestItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
        item: schemas.TestItemCreate,
        db: AsyncSession = Depends(get_db),
        _=Depends(dependencies.require_user)
):
    return await crud.create_test_item(db, item)

# Пакетное создание тестовых элементов
@app.post("/batch-items/", response_model=list[schemas.TestItemResponse], status_code=status.HTTP_201_CREATED)
async def create_batch_items(
    items: list[schemas.TestItemCreate],
    db: AsyncSession = Depends(get_db),
    _=Depends(dependencies.require_user)
):
    db_items = [TestTable(**item.dict()) for item in items]
    db.add_all(db_items)
    await db.commit()
    for db_item in db_items:
        await db.refresh(db_item)
    return db_items

# Загрузка данных из CSV
@app.post("/upload-csv/", response_model=list[schemas.TestItemResponse], status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(dependencies.require_user)
):
    try:
        # Сохраняем файл во временный файл на диске
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Читаем CSV из временного файла
        df = pd.read_csv(temp_file_path)
        items = df.to_dict(orient='records')
        validated_items = []
        for item in items:
            validated_item = schemas.TestItemCreate(**item)
            validated_items.append(validated_item)
        db_items = [TestTable(**item.dict()) for item in validated_items]
        db.add_all(db_items)
        await db.commit()
        for db_item in db_items:
            await db.refresh(db_item)

        # Удаляем временный файл
        os.remove(temp_file_path)
        return db_items
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error in CSV data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV file: {str(e)}"
        )

# Загрузка данных из Excel
@app.post("/upload-excel/", response_model=list[schemas.TestItemResponse], status_code=status.HTTP_201_CREATED)
async def upload_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(dependencies.require_user)
):
    try:
        # Сохраняем файл во временный файл на диске
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Читаем Excel из временного файла
        df = pd.read_excel(temp_file_path)
        items = df.to_dict(orient='records')
        validated_items = []
        for item in items:
            validated_item = schemas.TestItemCreate(**item)
            validated_items.append(validated_item)
        db_items = [TestTable(**item.dict()) for item in validated_items]
        db.add_all(db_items)
        await db.commit()
        for db_item in db_items:
            await db.refresh(db_item)

        # Удаляем временный файл
        os.remove(temp_file_path)
        return db_items
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error in Excel data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing Excel file: {str(e)}"
        )

# Получение списка тестовых элементов с фильтрацией
@app.get("/items/", response_model=list[schemas.TestItemResponse])
async def read_items(
    skip: int = 0,
    limit: int = 100,
    name: str = Query(None, description="Filter by name (partial match)"),
    value_min: int = Query(None, description="Minimum value filter"),
    value_max: int = Query(None, description="Maximum value filter"),
    db: AsyncSession = Depends(get_db),
    _=Depends(dependencies.require_user)
):
    return await crud.get_test_items(db, skip=skip, limit=limit, name=name, value_min=value_min, value_max=value_max)

# Получение одного тестового элемента
@app.get("/items/{item_id}", response_model=schemas.TestItemResponse)
async def read_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _=Depends(dependencies.require_user)
):
    item = await crud.get_test_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

# Обновление тестового элемента
@app.patch("/items/{item_id}", response_model=schemas.TestItemResponse)
async def update_item(
        item_id: int,
        item_update: schemas.TestItemUpdate,
        db: AsyncSession = Depends(get_db),
        _=Depends(dependencies.require_user)
):
    updated_item = await crud.update_test_item(db, item_id, item_update)
    if not updated_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item

# Удаление тестового элемента
@app.delete("/items/{item_id}")
async def delete_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _=Depends(dependencies.require_user)
):
    if not await crud.delete_test_item(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

# Создание комментария
@app.post("/items/{item_id}/comments", response_model=schemas.CommentResponse)
async def create_comment(
        item_id: int,
        comment: schemas.CommentCreate,
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(dependencies.require_user)
):
    """Добавление комментария к тестовому элементу"""
    item = await crud.get_test_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_comment = await crud.create_comment(db, item_id, comment, current_user["username"])
    return db_comment

# Получение комментариев
@app.get("/items/{item_id}/comments", response_model=list[schemas.CommentResponse])
async def read_comments(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _=Depends(dependencies.require_user)
):
    """Получение комментариев к тестовому элементу"""
    comments = await crud.get_comments(db, item_id)
    return comments

# Удаление комментария
@app.delete("/items/{item_id}/comments/{comment_id}")
async def delete_comment(
        item_id: int,
        comment_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(dependencies.require_user)
):
    """Удаление комментария"""
    comment = await crud.get_comment(db, comment_id)
    if not comment or comment.item_id != item_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    if current_user["role"] != "admin" and comment.author != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    await crud.delete_comment(db, comment_id)
    return {"message": "Comment deleted successfully"}

# Создание таблиц при запуске
@app.on_event("startup")
async def startup_event():
    """Создание таблиц при запуске приложения"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created")