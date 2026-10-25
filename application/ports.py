from typing import Protocol
from datetime import datetime

class Clock(Protocol):
    def now(self) -> datetime: ...

class PaymentSystem(Protocol):
    def charge(self, amount: float) -> bool: ...