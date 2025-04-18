from typing import List

from database.common.base import BaseModel as Base
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy import (
    func,
)
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class BaseDAO[M: Base]:
    model: type[M] | None = None

    def __init__(self, session: AsyncSession):
        self._session = session
        if self.model is None:
            raise ValueError(
                "Модель должна быть указана в дочернем классе"
            )

    def _get_sorting_attrs(self, sort_fields: list[str]):
        return (getattr(self.model, field) for field in sort_fields)

    async def find_one_or_none_by_id(self, data_id: int) -> M | None:
        try:
            query = select(self.model).filter_by(id=data_id)
            result = await self._session.execute(query)
            record = result.scalar_one_or_none()
            log_message = (
                f"Запись {self.model.__name__} с "
                f"ID {data_id} {'найдена' if record else 'не найдена'}."
            )
            logger.info(log_message)
            return record
        except SQLAlchemyError as e:
            logger.error(
                f"Ошибка при поиске записи с ID {data_id}: {e}"
            )
            raise

    async def find_one_or_none(self, filters: BaseModel) -> M | None:
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(
            f"Поиск одной записи {self.model.__name__} по фильтрам: {filter_dict}"
        )
        try:
            query = select(self.model).filter_by(**filter_dict)
            result = await self._session.execute(query)
            record = result.scalar_one_or_none()
            log_message = f"Запись {'найдена' if record else 'не найдена'} по фильтрам: {filter_dict}"
            logger.info(log_message)
            return record
        except SQLAlchemyError as e:
            logger.error(
                f"Ошибка при поиске записи по фильтрам {filter_dict}: {e}"
            )
            raise

    async def find_all(
        self,
        filters: BaseModel | None = None,
        sort_fields: list[str] | None = None,
    ) -> list[M]:
        filter_dict = (
            filters.model_dump(exclude_unset=True) if filters else {}
        )
        logger.info(
            f"Поиск всех записей {self.model.__name__} по фильтрам: {filter_dict}"
        )
        try:
            query = select(self.model).filter_by(**filter_dict)
            if sort_fields:
                query = query.order_by(
                    *self._get_sorting_attrs(sort_fields=sort_fields)
                )
            result = await self._session.execute(query)
            records = result.scalars().all()
            logger.info(f"Найдено {len(records)} записей.")
            return records
        except SQLAlchemyError as e:
            logger.error(
                f"Ошибка при поиске всех записей по фильтрам {filter_dict}: {e}"
            )
            raise

    async def add(self, values: BaseModel) -> M:
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(
            f"Добавление записи {self.model.__name__} с параметрами: {values_dict}"
        )
        try:
            new_instance = self.model(**values_dict)
            self._session.add(new_instance)
            await self._session.flush()
            logger.info(
                f"Запись {self.model.__name__} успешно добавлена."
            )
            return new_instance
        except SQLAlchemyError as e:
            logger.error("Ошибка при добавлении записи {}", e)
            await self._session.rollback()

    async def add_many(
        self,
        instances: List[BaseModel],
        exclude: set[str] | None = None,
    ) -> list[M]:
        values_list = [
            item.model_dump(exclude_unset=True, exclude=exclude)
            for item in instances
        ]
        logger.info(
            f"Добавление нескольких записей {self.model.__name__}. Количество: {len(values_list)}"
        )
        try:
            new_instances = [
                self.model(**values) for values in values_list
            ]
            self._session.add_all(new_instances)
            await self._session.flush()
            logger.info(
                f"Успешно добавлено {len(new_instances)} записей."
            )
            return new_instances
        except SQLAlchemyError as e:
            logger.error(
                f"Ошибка при добавлении нескольких записей: {e}"
            )
            raise

    async def update(
        self, filters: BaseModel, values: BaseModel
    ) -> int:
        filter_dict = filters.model_dump(exclude_unset=True)
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(
            f"Обновление записей {self.model.__name__} по фильтру: {filter_dict} с параметрами: {values_dict}"
        )
        try:
            query = (
                sqlalchemy_update(self.model)
                .where(
                    *[
                        getattr(self.model, k) == v
                        for k, v in filter_dict.items()
                    ]
                )
                .values(**values_dict)
                .execution_options(synchronize_session="fetch")
            )
            result = await self._session.execute(query)
            await self._session.flush()
            logger.info(f"Обновлено {result.rowcount} записей.")
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении записей: {e}")
            raise

    async def delete(self, filters: BaseModel) -> int:
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(
            f"Удаление записей {self.model.__name__} по фильтру: {filter_dict}"
        )
        if not filter_dict:
            logger.error("Нужен хотя бы один фильтр для удаления.")
            raise ValueError(
                "Нужен хотя бы один фильтр для удаления."
            )
        try:
            query = sqlalchemy_delete(self.model).filter_by(
                **filter_dict
            )
            result = await self._session.execute(query)
            await self._session.flush()
            logger.info(f"Удалено {result.rowcount} записей.")
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при удалении записей: {e}")
            raise

    async def count(self, filters: BaseModel | None = None):
        filter_dict = (
            filters.model_dump(exclude_unset=True) if filters else {}
        )
        logger.info(
            f"Подсчет количества записей {self.model.__name__} по фильтру: {filter_dict}"
        )
        try:
            query = select(func.count(self.model.id)).filter_by(
                **filter_dict
            )
            result = await self._session.execute(query)
            count = result.scalar()
            logger.info(f"Найдено {count} записей.")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при подсчете записей: {e}")
            raise

    async def bulk_update(self, records: List[BaseModel]):
        logger.info(
            f"Массовое обновление записей {self.model.__name__}"
        )
        try:
            updated_count = 0
            for record in records:
                record_dict = record.model_dump(exclude_unset=True)
                if "id" not in record_dict:
                    continue

                update_data = {
                    k: v for k, v in record_dict.items() if k != "id"
                }
                stmt = (
                    sqlalchemy_update(self.model)
                    .filter_by(id=record_dict["id"])
                    .values(**update_data)
                )
                result = await self._session.execute(stmt)
                updated_count += result.rowcount

            await self._session.flush()
            logger.info(f"Обновлено {updated_count} записей")
            return updated_count
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при массовом обновлении: {e}")
            raise
