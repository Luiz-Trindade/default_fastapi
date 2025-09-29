from os import cpu_count
from asyncio import Semaphore
from fastapi import APIRouter
from sqlmodel import Session, select
from config import engine
from models.user import User
from diskcache import Cache

router = APIRouter()

User.metadata.create_all(engine)

cache = Cache("./cache")

semaphore = Semaphore(cpu_count())


@router.post("/")
async def create_user(user: User):
    async with semaphore:
        with Session(engine) as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            cache.delete("users_all")
            cache.delete(f"user_{user.id}")
            return user


@router.get("/")
async def read_users():
    async with semaphore:
        if (users := cache.get("users_all")) is not None:
            return users
        with Session(engine) as session:
            users = session.exec(select(User)).all()
            cache.set("users_all", users)
            return users


@router.get("/{user_id}")
async def read_user(user_id: int):
    async with semaphore:
        if (user := cache.get(f"user_{user_id}")) is not None:
            return user
        with Session(engine) as session:
            user = session.get(User, user_id)
            if user:
                cache.set(f"user_{user_id}", user)
            return user


@router.patch("/{user_id}")
async def update_user(user_id: int, user_data: User):
    async with semaphore:
        with Session(engine) as session:
            user = session.get(User, user_id)
            if not user:
                return {"error": "User not found"}
            if user_data.name is not None:
                user.name = user_data.name
            if user_data.email is not None:
                user.email = user_data.email
            session.add(user)
            session.commit()
            session.refresh(user)
            cache.delete(f"user_{user_id}")
            cache.delete("users_all")
            return user


@router.delete("/{user_id}")
async def delete_user(user_id: int):
    async with semaphore:
        with Session(engine) as session:
            user = session.get(User, user_id)
            if not user:
                return {"error": "User not found"}
            session.delete(user)
            session.commit()
            cache.delete(f"user_{user_id}")
            cache.delete("users_all")
            return {"ok": True}
