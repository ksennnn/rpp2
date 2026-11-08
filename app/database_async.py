from datetime import datetime, time, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from .config import ASYNC_DATABASE_URL


# Создание асинхронного движка
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True
)


async def get_local_flights(day):
    """
    Асинхронное получение рейсов
    из собственной базы данных.
    """
    start = datetime.combine(day, time.min)
    finish = start + timedelta(days=1)

    query = text("""
        SELECT
            carrier,
            flight_no,
            origin,
            destination,
            departure::text AS departure,
            arrival::text AS arrival,
            price
        FROM flights
        WHERE departure >= :start
          AND departure < :finish
    """)

    async with engine.connect() as connection:
        result = await connection.execute(query, {"start": start, "finish": finish})
        rows = result.mappings().all()

    return [dict(row) for row in rows]