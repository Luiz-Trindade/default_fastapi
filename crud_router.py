from os import cpu_count
from asyncio import Semaphore
from typing import Type, TypeVar, Optional
from fastapi import APIRouter, HTTPException, status, Query
from sqlmodel import SQLModel, Session, select, func
from diskcache import Cache
from config import engine
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

# Cache global
cache = Cache("./cache")

# TypeVar para tipagem genérica
T = TypeVar("T", bound=SQLModel)


def crud_router(
    model: Type[T],
    prefix: str,
    ttl: int | None = None,
    max_concurrent: int | None = None,
) -> APIRouter:
    """
    Gera um router CRUD completo para um modelo SQLModel.

    Args:
        model: Classe do modelo SQLModel
        prefix: Prefixo da rota
        ttl: Tempo em segundos para expirar o cache. Se None, cache persiste indefinidamente
        max_concurrent: Número máximo de operações concorrentes. Se None, usa cpu_count()

    Returns:
        APIRouter configurado com endpoints CRUD
    """
    router = APIRouter()
    model_name = model.__name__.lower()

    # Semáforo específico para este modelo
    semaphore = Semaphore(max_concurrent or cpu_count())

    # Funções auxiliares
    def _set_cache(key: str, value: any, use_ttl: bool = True) -> None:
        """Define valor no cache com tratamento de erro."""
        try:
            # Serializa objetos SQLModel para dict
            if isinstance(value, list):
                serialized = [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in value
                ]
            elif hasattr(value, "model_dump"):
                serialized = value.model_dump()
            else:
                serialized = value

            if use_ttl and ttl:
                cache.set(key, serialized, expire=ttl)
            else:
                cache.set(key, serialized)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache para {key}: {e}")

    def _get_cache(key: str) -> any:
        """Obtém valor do cache com tratamento de erro."""
        try:
            return cache.get(key)
        except Exception as e:
            logger.warning(f"Erro ao ler cache para {key}: {e}")
            return None

    def _delete_cache(key: str) -> None:
        """Remove valor do cache com tratamento de erro."""
        try:
            cache.delete(key)
        except Exception as e:
            logger.warning(f"Erro ao deletar cache para {key}: {e}")

    def _invalidate_all_cache() -> None:
        """Invalida todos os caches relacionados ao modelo."""
        _delete_cache(f"{model_name}_all")
        # Invalida cache de contagem
        _delete_cache(f"{model_name}_count")

    # -------------------------
    # CREATE
    # -------------------------
    @router.post("/", status_code=status.HTTP_201_CREATED, response_model=model)
    async def create_item(item: model) -> model:  # type: ignore
        """Cria um novo item."""
        async with semaphore:
            with Session(engine) as session:
                session.add(item)
                session.commit()
                session.refresh(item)

                _invalidate_all_cache()
                _delete_cache(f"{model_name}_{item.id}")
                _set_cache(f"{model_name}_{item.id}", item)

                return item

    @router.post(
        "/bulk", status_code=status.HTTP_201_CREATED, response_model=list[model]
    )
    async def create_items(items: list[model]) -> list[model]:  # type: ignore
        """Cria múltiplos itens em lote."""
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lista de itens não pode estar vazia",
            )

        async with semaphore:
            with Session(engine) as session:
                session.add_all(items)
                session.commit()

                for item in items:
                    session.refresh(item)
                    _delete_cache(f"{model_name}_{item.id}")
                    _set_cache(f"{model_name}_{item.id}", item)

                _invalidate_all_cache()
                return items

    # -------------------------
    # READ
    # -------------------------
    @router.get("/", status_code=status.HTTP_200_OK)
    async def read_items(
        skip: int = Query(0, ge=0, description="Número de registros para pular"),
        limit: int = Query(
            100, ge=1, le=1000, description="Número máximo de registros"
        ),
    ):
        """Lista todos os itens com paginação."""
        async with semaphore:
            cache_key = f"{model_name}_all_{skip}_{limit}"

            if (cached_items := _get_cache(cache_key)) is not None:
                return cached_items

            with Session(engine) as session:
                items = session.exec(select(model).offset(skip).limit(limit)).all()
                _set_cache(cache_key, items)
                return items

    @router.get("/count", status_code=status.HTTP_200_OK)
    async def count_items():
        """Retorna o total de itens."""
        async with semaphore:
            cache_key = f"{model_name}_count"

            if (cached_count := _get_cache(cache_key)) is not None:
                return {"count": cached_count}

            with Session(engine) as session:
                count = session.exec(select(func.count()).select_from(model)).one()
                _set_cache(cache_key, count)
                return {"count": count}

    @router.get("/{item_id}", status_code=status.HTTP_200_OK, response_model=model)
    async def read_item(item_id: int) -> model:  # type: ignore
        """Busca um item específico por ID."""
        async with semaphore:
            if (cached_item := _get_cache(f"{model_name}_{item_id}")) is not None:
                return cached_item

            with Session(engine) as session:
                item = session.get(model, item_id)
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{model.__name__} com ID {item_id} não encontrado",
                    )

                _set_cache(f"{model_name}_{item_id}", item)
                return item

    # -------------------------
    # UPDATE
    # -------------------------
    @router.patch("/{item_id}", status_code=status.HTTP_200_OK, response_model=model)
    async def update_item(item_id: int, item_data: model) -> model:  # type: ignore
        """Atualiza um item existente."""
        async with semaphore:
            with Session(engine) as session:
                item = session.get(model, item_id)
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{model.__name__} com ID {item_id} não encontrado",
                    )

                # Usa model_dump em vez de dict para compatibilidade
                update_data = item_data.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(item, key, value)

                session.add(item)
                session.commit()
                session.refresh(item)

                _delete_cache(f"{model_name}_{item_id}")
                _invalidate_all_cache()
                _set_cache(f"{model_name}_{item_id}", item)

                return item

    @router.patch("/bulk", status_code=status.HTTP_200_OK, response_model=list[model])
    async def update_items(items_data: list[dict]) -> list[model]:  # type: ignore
        """Atualiza múltiplos itens em lote."""
        if not items_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lista de itens não pode estar vazia",
            )

        # Valida se todos têm ID
        if any("id" not in data for data in items_data):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Todos os itens devem ter um campo 'id'",
            )

        async with semaphore:
            updated = []
            with Session(engine) as session:
                for data in items_data:
                    item = session.get(model, data.get("id"))
                    if not item:
                        logger.warning(
                            f"Item com ID {data.get('id')} não encontrado, pulando"
                        )
                        continue

                    for key, value in data.items():
                        if key != "id" and hasattr(item, key):
                            setattr(item, key, value)

                    session.add(item)
                    updated.append(item)

                session.commit()

                # Atualiza cache dos itens modificados
                for item in updated:
                    session.refresh(item)
                    _delete_cache(f"{model_name}_{item.id}")
                    _set_cache(f"{model_name}_{item.id}", item)

                _invalidate_all_cache()

            return updated

    # -------------------------
    # DELETE
    # -------------------------
    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(item_id: int) -> None:
        """Deleta um item específico."""
        async with semaphore:
            with Session(engine) as session:
                item = session.get(model, item_id)
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{model.__name__} com ID {item_id} não encontrado",
                    )

                session.delete(item)
                session.commit()

                _delete_cache(f"{model_name}_{item_id}")
                _invalidate_all_cache()

    @router.delete("/bulk", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_items(ids: list[int]) -> None:
        """Deleta múltiplos itens em lote."""
        if not ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lista de IDs não pode estar vazia",
            )

        async with semaphore:
            deleted_count = 0
            with Session(engine) as session:
                for item_id in ids:
                    item = session.get(model, item_id)
                    if item:
                        session.delete(item)
                        _delete_cache(f"{model_name}_{item_id}")
                        deleted_count += 1
                    else:
                        logger.warning(f"Item com ID {item_id} não encontrado, pulando")

                session.commit()
                _invalidate_all_cache()

            logger.info(f"Deletados {deleted_count} de {len(ids)} itens solicitados")

    return router
