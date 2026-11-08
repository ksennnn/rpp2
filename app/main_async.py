import asyncio
import time
import httpx

from datetime import date
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException

from .config import SUPPLIERS, SUPPLIER_TIMEOUT, RETRY_DELAY
from .database_async import get_local_flights, engine
from .route_builder import build_routes


@asynccontextmanager
async def lifespan(app):
    # Создание HTTP-клиента при запуске
    app.state.client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )
    yield
    # Закрытие клиента
    await app.state.client.aclose()
    # Закрытие движка БД
    await engine.dispose()


app = FastAPI(title="Flight Search API - Async", lifespan=lifespan)


async def get_supplier_flights(client, url, day):
    """
    Асинхронный запрос поставщику.

    В общий бюджет 2 секунды входят:
    первая попытка, повтор и пауза.
    """
    try:
        async with asyncio.timeout(SUPPLIER_TIMEOUT):
            for attempt in range(2):
                try:
                    response = await client.get(
                        url + "/flights",
                        params={"date": day.isoformat()},
                        timeout=1.7
                    )
                    response.raise_for_status()
                    return response.json(), False
                except httpx.HTTPError:
                    if attempt == 0:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return [], True
            return [], True
    except TimeoutError:
        return [], True


@app.get("/search")
async def search(
    origin: str,
    destination: str,
    flight_date: date = Query(alias="date")
):
    start_time = time.perf_counter()

    # Подготовка одновременно выполняемых задач
    tasks = [
        get_local_flights(flight_date),
        *[
            get_supplier_flights(app.state.client, supplier_url, flight_date)
            for supplier_url in SUPPLIERS
        ]
    ]

    # Одновременное выполнение
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Результат собственной базы
    local_flights = results[0]
    if isinstance(local_flights, Exception):
        raise HTTPException(status_code=503, detail="Database is unavailable")

    all_flights = list(local_flights)
    failed_suppliers = []

    # Обработка поставщиков
    for i, result in enumerate(results[1:], start=1):
        if isinstance(result, Exception):
            failed_suppliers.append(f"supplier{i}")
            continue
        flights, failed = result
        all_flights.extend(flights)
        if failed:
            failed_suppliers.append(f"supplier{i}")

    # Построение маршрутов
    routes = build_routes(all_flights, origin, destination, flight_date)

    processing_time = (time.perf_counter() - start_time) * 1000
    unavailable = not local_flights and len(failed_suppliers) == 3

    return {
        "routes": routes,
        "failed_suppliers": failed_suppliers,
        "processing_ms": round(processing_time, 2),
        "unavailable": unavailable,
        "message": "Поиск временно недоступен" if unavailable else None
    }


@app.get("/health")
async def health():
    return {"status": "ok"}