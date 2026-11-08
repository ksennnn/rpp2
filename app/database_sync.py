from datetime import datetime, time, timedelta
from sqlalchemy import create_engine, text
from .config import DATABASE_URL


# Создание синхронного движка БД
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True
)

def get_local_flights(day):
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

    with engine.connect() as connection:
        result = connection.execute(query, {"start": start, "finish": finish})
        rows = result.mappings().all()

    return [dict(row) for row in rows]