from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from pydantic import BaseModel

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Any] = None,
    ) -> tuple[List[ModelType], int]:
        query = select(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)

        if order_by is not None:
            query = query.order_by(order_by)
        else:
            query = query.order_by(self.model.id.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar_one()

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total_count

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | Dict[str, Any],
    ) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> ModelType:
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj
