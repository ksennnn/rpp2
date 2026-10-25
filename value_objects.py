from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from .exceptions import InvalidValueObject

@dataclass(frozen=True)
class BookId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("BookId должен быть UUID")

@dataclass(frozen=True)
class ReaderId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("ReaderId должен быть UUID")

@dataclass(frozen=True)
class CopyId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("CopyId должен быть UUID")

@dataclass(frozen=True)
class LoanId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise InvalidValueObject("LoanId должен быть UUID")

@dataclass(frozen=True)
class ISBN:
    value: str

    def __post_init__(self):
        digits = self.value.replace("-", "").strip()
        if not digits.isdigit() or len(digits) not in (10, 13):
            raise InvalidValueObject(
                f"ISBN должен содержать 10 или 13 цифр, получено: {self.value!r}"
            )

@dataclass(frozen=True)
class LoanPeriod:
    issue_date: date
    due_date: date

    def __post_init__(self):
        if self.due_date < self.issue_date:
            raise InvalidValueObject(
                "Дата возврата не может быть раньше даты выдачи"
            )

    def is_overdue(self, return_date: date) -> bool:
        return return_date > self.due_date

@dataclass(frozen=True)
class Fine:
    amount: Decimal

    def __post_init__(self):
        if self.amount < 0:
            raise InvalidValueObject("Сумма штрафа не может быть отрицательной")

    @classmethod
    def zero(cls) -> "Fine":
        return cls(amount=Decimal("0"))