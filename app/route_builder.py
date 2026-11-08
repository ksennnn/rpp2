from datetime import datetime


def parse_datetime(value):
    """
    Преобразование даты в datetime.
    """

    if isinstance(value, datetime):
        return value

    return datetime.fromisoformat(str(value))


def build_routes(flights, origin, destination, search_date, limit=20):
    # Индексирование рейсов по аэропорту вылета
    flights_by_origin = {}
    for flight in flights:
        airport = flight["origin"].strip()
        flights_by_origin.setdefault(airport, []).append(flight)

    found_routes = []

    def walk(current_airport, path, visited_airports):
        # Если достигнут аэропорт назначения
        if path and current_airport == destination:
            total_price = sum(float(flight["price"]) for flight in path)
            found_routes.append({
                "flights": path.copy(),
                "price": round(total_price, 2)
            })
            return
        # Не больше трёх рейсов:
        # прямой + максимум две пересадки
        if len(path) >= 3:
            return
        for flight in flights_by_origin.get(current_airport, []):
            next_airport = flight["destination"].strip()
            # Проверка повторного аэропорта
            if next_airport in visited_airports:
                continue

            departure = parse_datetime(flight["departure"])
            # Все рейсы должны вылетать в дату поиска
            if departure.date() != search_date:
                continue

            # Проверка времени пересадки
            if path:
                previous_arrival = parse_datetime(path[-1]["arrival"])
                transfer_hours = (departure - previous_arrival).total_seconds() / 3600
                if not 1 <= transfer_hours <= 6:
                    continue

            walk(next_airport, path + [flight], visited_airports | {next_airport})

    walk(origin, [], {origin})

    # Сортировка по стоимости
    found_routes.sort(key=lambda route: route["price"])
    # Возвращаем 20 самых дешёвых
    result = []

    for route in found_routes[:limit]:
        normalized_flights = []

        for flight in route["flights"]:

            normalized_flights.append({
                "carrier": flight["carrier"],
                "flight_no": flight["flight_no"],
                "origin": flight["origin"],
                "destination": flight["destination"],
                "departure": str(flight["departure"]),
                "arrival": str(flight["arrival"]),
                "price": float(flight["price"])
            })

        result.append({
            "flights": normalized_flights,
            "price": route["price"]
        })

    return result