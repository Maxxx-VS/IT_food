"""
Файл содержит функции для выполнения CRUD (Create, Read, Update, Delete)
операций с базой данных, включая создание пользователей и тестовых элементов,
а также получение пользователей и тестовых элементов.
"""

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from .models import TestTable, User, RefreshToken, Comment
from . import schemas
from passlib.context import CryptContext

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Функции для пользователей
async def get_user(db: AsyncSession, username: str):
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(db: AsyncSession, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def update_user(db: AsyncSession, username: str, user_update: schemas.UserUpdate):
    stmt = update(User).where(User.username == username)
    values = {}
    if user_update.password:
        values["hashed_password"] = pwd_context.hash(user_update.password)
    if user_update.role:
        values["role"] = user_update.role
    if values:
        await db.execute(stmt.values(**values))
        await db.commit()
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()


async def delete_user(db: AsyncSession, username: str):
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    if user:
        await db.execute(delete(User).where(User.username == username))
        await db.commit()
        return True
    return False


# Функции для refresh-токенов
async def get_refresh_token(db: AsyncSession, token: str):
    result = await db.execute(select(RefreshToken).filter(RefreshToken.token == token))
    return result.scalars().first()


async def create_refresh_token(db: AsyncSession, user_id: int, token: str, expires_at):
    db_token = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token


async def delete_refresh_token(db: AsyncSession, token: str):
    await db.execute(delete(RefreshToken).where(RefreshToken.token == token))
    await db.commit()


# Функции для тестовых элементов
async def create_test_item(db: AsyncSession, item: schemas.TestItemCreate):
    db_item = TestTable(**item.dict())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def get_test_items(db: AsyncSession, skip: int = 0, limit: int = 100, name: str = None, value_min: int = None,
                         value_max: int = None):
    query = select(TestTable)

    # Добавляем фильтры, если параметры указаны
    if name:
        query = query.filter(TestTable.name.ilike(f"%{name}%"))
    if value_min is not None:
        query = query.filter(TestTable.value >= value_min)
    if value_max is not None:
        query = query.filter(TestTable.value <= value_max)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_test_item(db: AsyncSession, item_id: int):
    result = await db.execute(select(TestTable).filter(TestTable.id == item_id))
    return result.scalars().first()


async def update_test_item(db: AsyncSession, item_id: int, item_update: schemas.TestItemUpdate):
    stmt = update(TestTable).where(TestTable.id == item_id)
    values = {k: v for k, v in item_update.dict(exclude_unset=True).items()}
    if values:
        await db.execute(stmt.values(**values))
        await db.commit()
    result = await db.execute(select(TestTable).filter(TestTable.id == item_id))
    return result.scalars().first()


async def delete_test_item(db: AsyncSession, item_id: int):
    result = await db.execute(select(TestTable).filter(TestTable.id == item_id))
    item = result.scalars().first()
    if item:
        await db.execute(delete(TestTable).where(TestTable.id == item_id))
        await db.commit()
        return True
    return False


# Функции для комментариев
async def create_comment(db: AsyncSession, item_id: int, comment: schemas.CommentCreate, author: str):
    db_comment = Comment(item_id=item_id, text=comment.text, author=author)
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment


async def get_comments(db: AsyncSession, item_id: int):
    result = await db.execute(select(Comment).filter(Comment.item_id == item_id))
    return result.scalars().all()


async def get_comment(db: AsyncSession, comment_id: int):
    result = await db.execute(select(Comment).filter(Comment.id == comment_id))
    return result.scalars().first()


async def delete_comment(db: AsyncSession, comment_id: int):
    await db.execute(delete(Comment).where(Comment.id == comment_id))
    await db.commit()


# Функции для аутентификации
class Auth:
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict):
        from datetime import datetime, timedelta
        from jose import jwt
        from .config import settings

        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_refresh_token(token: str):
        from jose import jwt, JWTError
        from .config import settings

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None


auth = Auth()