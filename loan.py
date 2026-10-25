from datetime import date
from decimal import Decimal

from .exceptions import DomainInvariantViolation
from .value_objects import BookId, CopyId, Fine, LoanId, LoanPeriod, ReaderId
from .states import ReservedState
from .events import *

class Loan:
    def __init__(self, loan_id: LoanId, book_id: BookId, copy_id: CopyId, reader_id: ReaderId, period: LoanPeriod, now):
        self._id = loan_id
        self._book_id = book_id
        self._copy_id = copy_id
        self._reader_id = reader_id
        self._period = period
        self._return_date: date | None = None
        self._fine: Fine = Fine.zero()
        
        # поля для паттерна State 
        self._state = ReservedState()
        self._events = [LoanCreated(str(loan_id.value), now)]

    @property
    def id(self) -> LoanId: return self._id
    @property
    def book_id(self) -> BookId: return self._book_id
    @property
    def copy_id(self) -> CopyId: return self._copy_id
    @property
    def reader_id(self) -> ReaderId: return self._reader_id
    @property
    def period(self) -> LoanPeriod: return self._period
    @property
    def return_date(self) -> date | None: return self._return_date
    @property
    def fine(self) -> Fine: return self._fine
    @property
    def is_closed(self) -> bool: return self._return_date is not None

    # свойства для State 
    @property
    def status(self) -> str: return self._state.name
    @property
    def allowed_events(self) -> frozenset: return self._state.allowed_events
    @property
    def events(self) -> tuple: return tuple(self._events)

    # методы событий (делегирование в State) 
    def checkout(self, now):
        self._state = self._state.checkout(self, now)
        self._events.append(BookIssued(str(self.id.value), now))

    def return_book(self, now, is_damaged, fine_tariff: Decimal = Decimal("10")):
        return_date = now.date()
        
        if return_date < self._period.issue_date:
            raise DomainInvariantViolation("Дата возврата не может быть раньше даты выдачи")

        # считаем штраф
        self._return_date = return_date
        if self._period.is_overdue(return_date):
            days_overdue = (return_date - self._period.due_date).days
            self._fine = Fine(amount=fine_tariff * days_overdue)
        if is_damaged:
            self._fine = Fine(amount=self._fine.amount + Decimal("500"))

        self._state = self._state.return_book(self, now, is_damaged)
        self._events.append(BookReturned(str(self.id.value), float(self._fine.amount), is_damaged, now))

    def extend(self, now, has_queue: bool):
        self._state = self._state.extend(self, now, has_queue)

    def cancel(self, now):
        self._state = self._state.cancel(self, now)
        self._events.append(LoanCancelled(str(self.id.value), now))

    def expire_14d(self, now):
        self._state = self._state.expire_14d(self, now)
        self._events.append(LoanOverdue(str(self.id.value), now))

    def expire_30d(self, now):
        self._state = self._state.expire_30d(self, now)
        self._events.append(LoanBlocked(str(self.id.value), now))

    def reject(self, now):
        self._state = self._state.reject(self, now)
