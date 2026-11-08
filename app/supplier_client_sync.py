import time
import requests

from .config import (
    SUPPLIER_TIMEOUT,
    RETRY_DELAY
)


def get_supplier_flights(url, day):
    deadline = (time.monotonic() + SUPPLIER_TIMEOUT)
    for attempt in range(2):
        remaining = (deadline - time.monotonic())
        if remaining <= 0:
            return [], True

        try:

            response = requests.get(
                url + "/flights",
                params={"date": day.isoformat()},
                timeout=remaining
            )
            response.raise_for_status()
            return response.json(), False

        except (
            requests.RequestException,
            ValueError
        ):
            # Повтор только один раз
            if attempt == 0:
                remaining = (deadline - time.monotonic())
                if remaining <= RETRY_DELAY:
                    return [], True

                time.sleep(RETRY_DELAY)

    return [], True