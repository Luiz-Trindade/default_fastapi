from os import cpu_count
from asyncio import Semaphore
from typing import Type
from fastapi import APIRouter, HTTPException, status
from sqlmodel import SQLModel, Session, select
from diskcache import Cache
from config import engine

semaphore = Semaphore(cpu_count())
cache = Cache("./cache")


def crud_router(
    model: Type[SQLModel], prefix: str, ttl: int | None = None
) -> APIRouter:
    """
    ttl: tempo em segundos para expirar o cache. Se None, cache persiste indefinidamente.
    """
    router = APIRouter()
    model.metadata.create_all(engine)
    model_name = model.__name__.lower()

    # -------------------------
    # CREATE
    # -------------------------
    @router.post("/", status_code=status.HTTP_201_CREATED)
    async def create_item(item: model):  # type: ignore
        async with semaphore:
            with Session(engine) as session:
                session.add(item)
                session.commit()
                session.refresh(item)
                cache.delete(f"{model_name}_all")
                cache.delete(f"{model_name}_{item.id}")
                if ttl:
                    cache.set(f"{model_name}_{item.id}", item, expire=ttl)
                return item

    @router.post("/bulk", status_code=status.HTTP_201_CREATED)
    async def create_items(items: list[model]):  # type: ignore
        async with semaphore:
            with Session(engine) as session:
                session.add_all(items)
                session.commit()
                for item in items:
                    session.refresh(item)
                    cache.delete(f"{model_name}_{item.id}")
                    if ttl:
                        cache.set(f"{model_name}_{item.id}", item, expire=ttl)
                cache.delete(f"{model_name}_all")
                return items

    # -------------------------
    # READ
    # -------------------------
    @router.get("/", status_code=status.HTTP_200_OK)
    async def read_items():
        async with semaphore:
            if (items := cache.get(f"{model_name}_all")) is not None:
                return items
            with Session(engine) as session:
                items = session.exec(select(model)).all()
                (
                    cache.set(f"{model_name}_all", items, expire=ttl)
                    if ttl
                    else cache.set(f"{model_name}_all", items)
                )
                return items

    @router.get("/{item_id}", status_code=status.HTTP_200_OK)
    async def read_item(item_id: int):
        async with semaphore:
            if (item := cache.get(f"{model_name}_{item_id}")) is not None:
                return item
            with Session(engine) as session:
                item = session.get(model, item_id)
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{model_name} not found",
                    )
                (
                    cache.set(f"{model_name}_{item_id}", item, expire=ttl)
                    if ttl
                    else cache.set(f"{model_name}_{item_id}", item)
                )
                return item

    # -------------------------
    # UPDATE
    # -------------------------
    @router.patch("/{item_id}", status_code=status.HTTP_200_OK)
    async def update_item(item_id: int, item_data: model):  # type: ignore
        async with semaphore:
            with Session(engine) as session:
                item = session.get(model, item_id)
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{model_name} not found",
                    )
                for key, value in item_data.dict(exclude_unset=True).items():
                    setattr(item, key, value)
                session.add(item)
                session.commit()
                session.refresh(item)
                cache.delete(f"{model_name}_{item_id}")
                cache.delete(f"{model_name}_all")
                if ttl:
                    cache.set(f"{model_name}_{item_id}", item, expire=ttl)
                return item

    @router.patch("/bulk", status_code=status.HTTP_200_OK)
    async def update_items(items_data: list[dict]):
        async with semaphore:
            updated = []
            with Session(engine) as session:
                for data in items_data:
                    item = session.get(model, data.get("id"))
                    if not item:
                        continue
                    for key, value in data.items():
                        if key != "id":
                            setattr(item, key, value)
                    session.add(item)
                    session.commit()
                    session.refresh(item)
                    cache.delete(f"{model_name}_{item.id}")
                    if ttl:
                        cache.set(f"{model_name}_{item.id}", item, expire=ttl)
                    updated.append(item)
                cache.delete(f"{model_name}_all")
            return updated

    # -------------------------
    # DELETE
    # -------------------------
    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(item_id: int):
        async with semaphore:
            with Session(engine) as session:
                item = session.get(model, item_id)
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{model_name} not found",
                    )
                session.delete(item)
                session.commit()
                cache.delete(f"{model_name}_{item_id}")
                cache.delete(f"{model_name}_all")
                return None

    @router.delete("/bulk", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_items(ids: list[int]):
        async with semaphore:
            with Session(engine) as session:
                for item_id in ids:
                    item = session.get(model, item_id)
                    if item:
                        session.delete(item)
                        cache.delete(f"{model_name}_{item_id}")
                session.commit()
                cache.delete(f"{model_name}_all")
                return None

    return router
