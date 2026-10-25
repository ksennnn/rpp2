from datetime import datetime, timedelta
from uuid import UUID
from application.ports import Clock
from domain.book import Book
from domain.exceptions import EntityNotFound
from domain.loan import Loan
from domain.reader import Reader
from domain.value_objects import BookId, LoanId, ReaderId

class InMemoryBookRepository:
    def __init__(self): self._storage: dict[UUID, Book] = {}
    def get(self, book_id: BookId) -> Book:
        try: return self._storage[book_id.value]
        except KeyError: raise EntityNotFound(f"Book {book_id.value} не найден")
    def save(self, book: Book): self._storage[book.id.value] = book

class InMemoryReaderRepository:
    def __init__(self): self._storage: dict[UUID, Reader] = {}
    def get(self, reader_id: ReaderId) -> Reader:
        try: return self._storage[reader_id.value]
        except KeyError: raise EntityNotFound(f"Reader {reader_id.value} не найден")
    def save(self, reader: Reader): self._storage[reader.id.value] = reader

class InMemoryLoanRepository:
    def __init__(self): self._storage: dict[UUID, Loan] = {}
    def get(self, loan_id: LoanId) -> Loan:
        try: return self._storage[loan_id.value]
        except KeyError: raise EntityNotFound(f"Loan {loan_id.value} не найден")
    def save(self, loan: Loan): self._storage[loan.id.value] = loan
    def get_all(self): return list(self._storage.values())

class ShiftedClock(Clock):
    def __init__(self): self._offset = timedelta(0)
    def now(self) -> datetime: return datetime.now() + self._offset
    def set_time(self, target_time: datetime):
        if target_time < datetime.now():
            raise ValueError("Нельзя перевести часы назад")
        self._offset = target_time - datetime.now()

class InMemoryPaymentSystem:
    def charge(self, amount: float) -> bool:
        print(f"[PaymentSystem] Списываем {amount} руб.")
        return True
