import time

from datetime import date

from fastapi import FastAPI, Query

from .config import SUPPLIERS

from .database_sync import get_local_flights

from .supplier_client_sync import (
    get_supplier_flights
)

from .route_builder import build_routes


app = FastAPI(
    title="Flight Search API - Async Blocking"
)


@app.get("/search")
async def search(

    origin: str,

    destination: str,

    flight_date: date = Query(alias="date")

):

    start_time = time.perf_counter()

    # Блокирующее обращение к БД
    local_flights = get_local_flights(
        flight_date
    )

    all_flights = list(local_flights)

    failed_suppliers = []

    # Последовательные блокирующие запросы
    for i, supplier_url in enumerate(
        SUPPLIERS,
        start=1
    ):

        flights, failed = get_supplier_flights(
            supplier_url,
            flight_date
        )

        all_flights.extend(flights)

        if failed:

            failed_suppliers.append(
                f"supplier{i}"
            )

    routes = build_routes(
        all_flights,
        origin,
        destination,
        flight_date
    )

    processing_time = (
        time.perf_counter() - start_time
    ) * 1000

    unavailable = (
        not local_flights
        and len(failed_suppliers) == 3
    )

    return {

        "routes": routes,

        "failed_suppliers": failed_suppliers,

        "processing_ms": round(
            processing_time,
            2
        ),

        "unavailable": unavailable
    }


@app.get("/health")
async def health():

    return {
        "status": "ok"
    }