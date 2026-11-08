import os
import random
import asyncio

from datetime import date as date_class
from datetime import datetime, time, timedelta

from fastapi import FastAPI, HTTPException


app = FastAPI()


SUPPLIER_ID = int(os.getenv("SUPPLIER_ID", "1"))
MEAN_MS = int(os.getenv("MEAN_MS", "300"))
ERROR_PCT = float(os.getenv("ERROR_PCT", "5"))
SLOW_PCT = float(os.getenv("SLOW_PCT", "0"))
FLIGHTS_PER_DAY = int(os.getenv("FLIGHTS_PER_DAY", "500"))


AIRPORTS = [
    f"A{chr(65 + i // 26)}{chr(65 + i % 26)}"
    for i in range(30)
]


def generate_flights(day):
    rng = random.Random(
        f"supplier:{SUPPLIER_ID}:{day}"
    )

    current_date = date_class.fromisoformat(day)

    flights = []

    for i in range(FLIGHTS_PER_DAY):

        origin, destination = rng.sample(
            AIRPORTS,
            2
        )

        departure = (
            datetime.combine(current_date, time(5, 0))
            + timedelta(minutes=rng.randrange(17 * 60))
        )

        duration = timedelta(
            minutes=rng.randint(60, 360)
        )

        arrival = departure + duration

        flights.append({
            "carrier": f"SUP{SUPPLIER_ID}",
            "flight_no": f"S{SUPPLIER_ID}{i:04d}",
            "origin": origin,
            "destination": destination,
            "departure": departure.isoformat(),
            "arrival": arrival.isoformat(),
            "price": round(rng.uniform(40, 400), 2)
        })

    return flights


@app.get("/flights")
async def get_flights(date: str):

    try:
        date_class.fromisoformat(date)

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Incorrect date format"
        )

    # Имитация дополнительной задержки 3 секунды
    if random.random() < SLOW_PCT / 100:

        await asyncio.sleep(3)

    else:

        delay = max(
            0,
            random.gauss(
                MEAN_MS,
                MEAN_MS * 0.3
            )
        ) / 1000

        await asyncio.sleep(delay)

    # Имитация ошибки HTTP 500
    if random.random() < ERROR_PCT / 100:

        raise HTTPException(
            status_code=500,
            detail="Supplier error"
        )

    return generate_flights(date)


@app.get("/health")
def health():

    return {
        "status": "ok",
        "supplier": SUPPLIER_ID
    }