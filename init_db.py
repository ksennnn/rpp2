import random
from datetime import date, datetime, time, timedelta
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL


# Дата начала генерации
START_DATE = date(2026, 11, 1)

# Количество дней
DAYS = 120

# Количество рейсов в сутки
FLIGHTS_PER_DAY = 1500

# Список 30 аэропортов
AIRPORTS = [
    f"A{chr(65 + i // 26)}{chr(65 + i % 26)}"
    for i in range(30)
]

engine = create_engine(DATABASE_URL)

def main():
    with engine.begin() as connection:
        # Создание таблицы
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS flights (
                id BIGSERIAL PRIMARY KEY,
                carrier TEXT NOT NULL,
                flight_no TEXT NOT NULL,
                origin CHAR(3) NOT NULL,
                destination CHAR(3) NOT NULL,
                departure TIMESTAMP NOT NULL,
                arrival TIMESTAMP NOT NULL,
                price NUMERIC(10, 2) NOT NULL
            )
        """))

        # Индекс для поиска по дате вылета
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS
            idx_flights_departure_origin
            ON flights(departure, origin)
        """))

        # Очистка старых записей
        connection.execute(
            text("TRUNCATE TABLE flights RESTART IDENTITY")
        )

        # SQL для добавления рейсов
        insert_query = text("""
            INSERT INTO flights (
                carrier,
                flight_no,
                origin,
                destination,
                departure,
                arrival,
                price
            )
            VALUES (
                :carrier,
                :flight_no,
                :origin,
                :destination,
                :departure,
                :arrival,
                :price
            )
        """)

        # Генерация на 120 дней
        for day_number in range(DAYS):

            current_date = (
                START_DATE
                + timedelta(days=day_number)
            )

            # Фиксированное начальное значение
            rng = random.Random(
                f"local:{current_date.isoformat()}"
            )

            flights = []

            for i in range(FLIGHTS_PER_DAY):
                origin, destination = rng.sample(
                    AIRPORTS,
                    2
                )

                # Время вылета
                departure = (
                    datetime.combine(
                        current_date,
                        time(5, 0)
                    )
                    + timedelta(
                        minutes=rng.randrange(17 * 60)
                    )
                )

                # Продолжительность полёта от 1 до 6 часов
                duration = timedelta(
                    minutes=rng.randint(60, 360)
                )

                arrival = departure + duration

                # Стоимость билета
                price = round(
                    rng.uniform(30, 350),
                    2
                )

                flights.append({

                    "carrier": "LOCAL",
                    "flight_no": (
                        f"L{day_number:03d}{i:04d}"
                    ),
                    "origin": origin,
                    "destination": destination,
                    "departure": departure,
                    "arrival": arrival,
                    "price": price

                })

            # Загрузка рейсов за сутки
            connection.execute(
                insert_query,
                flights
            )

            print(
                f"Загружен день {day_number + 1}/{DAYS}"
            )

    print("Генерация рейсов завершена!")


if __name__ == "__main__":

    main()